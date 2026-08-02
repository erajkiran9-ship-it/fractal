"""Agentic runner backed by an Azure OpenAI chat-completions deployment."""

import json

from backend.agent.azure_openai import (
    AzureOpenAIError,
    chat_completion,
    extract_json_object,
    message_text,
    response_message,
)
from backend.agent.system_prompt import build_system_prompt
from backend.agent.tools import TOOL_DEFINITIONS, execute_tool
from backend.config import DATA_DIR
from backend.workflow_plan import WorkflowPlanError, parse_workflow_plan


def _build_tools() -> list[dict]:
    """Translate the canonical tool definitions to OpenAI tool schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": definition["name"],
                "description": definition["description"],
                "parameters": definition["input_schema"],
            },
        }
        for definition in TOOL_DEFINITIONS
    ]


def _tool_arguments(tool_call: dict) -> tuple[str, dict]:
    function = tool_call.get("function") or {}
    tool_name = str(function.get("name") or "")
    raw_arguments = function.get("arguments") or "{}"
    if isinstance(raw_arguments, dict):
        tool_input = raw_arguments
    else:
        try:
            tool_input = json.loads(raw_arguments)
        except json.JSONDecodeError:
            tool_input = {"_invalid_arguments": str(raw_arguments)}
    if not isinstance(tool_input, dict):
        tool_input = {"_invalid_arguments": str(raw_arguments)}
    return tool_name, tool_input


def run_daily_cycle(current_date: str) -> dict:
    """Run one multi-turn collections cycle with Azure OpenAI tool calling."""
    system_prompt = build_system_prompt(current_date)
    tool_calls_log = []
    agent_reasoning = []
    messages = [
        {"role": "developer", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Run your daily collections cycle for today ({current_date}). "
                "Check for new invoices, new events, and process all open invoices. "
                "Take all appropriate actions."
            ),
        },
    ]

    max_iterations = 25
    has_tool_calls = False
    provider_error = False

    for iteration in range(max_iterations):
        try:
            result = chat_completion(messages, tools=_build_tools())
            assistant_message = response_message(result)
        except AzureOpenAIError as exc:
            agent_reasoning.append(f"API Error: {exc}")
            provider_error = True
            has_tool_calls = False
            break

        text = message_text(assistant_message)
        if text:
            agent_reasoning.append(text)

        tool_calls = assistant_message.get("tool_calls") or []
        has_tool_calls = bool(tool_calls)
        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.get("content"),
                **({"tool_calls": tool_calls} if tool_calls else {}),
            }
        )

        if not tool_calls:
            break

        for tool_call in tool_calls:
            tool_name, tool_input = _tool_arguments(tool_call)
            if "_invalid_arguments" in tool_input:
                result_str = json.dumps(
                    {
                        "error": (
                            f"Invalid JSON arguments for tool {tool_name}: "
                            f"{tool_input['_invalid_arguments'][:300]}"
                        )
                    }
                )
            elif not tool_name:
                result_str = json.dumps({"error": "Tool call did not include a name"})
            else:
                if "plan" in tool_input and isinstance(tool_input["plan"], str):
                    try:
                        tool_input["plan"] = parse_workflow_plan(tool_input["plan"])
                    except WorkflowPlanError:
                        pass
                result_str = execute_tool(tool_name, tool_input, current_date)

            tool_calls_log.append(
                {
                    "tool": tool_name or "unknown",
                    "input": tool_input,
                    "result_preview": (
                        result_str[:500] if len(result_str) > 500 else result_str
                    ),
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": result_str,
                }
            )

    from backend.data_layer import excel_store as db

    state = db.get_system_state()
    if not provider_error:
        state["last_cycle_date"] = current_date
        state["cycle_count"] = state.get("cycle_count", 0) + 1
        db.save_system_state(state)

    if provider_error:
        status = "error"
    elif has_tool_calls:
        status = "max_iterations_reached"
    else:
        status = "completed"

    return {
        "date": current_date,
        "cycle_number": state.get("cycle_count", 0),
        "iterations": min(iteration + 1, max_iterations),
        "tool_calls": len(tool_calls_log),
        "tool_calls_log": tool_calls_log,
        "agent_reasoning": "\n\n".join(agent_reasoning),
        "status": status,
        "provider": "azure_openai",
    }


def parse_invoice_with_vision(current_date: str, filename: str) -> dict:
    """Extract PDF text locally and structure it with Azure OpenAI."""
    import pdfplumber

    filepath = DATA_DIR / "incoming_invoices" / filename
    if not filepath.exists():
        return {"error": f"File not found: {filename}"}

    extracted_text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
                for table in page.extract_tables():
                    for row in table:
                        if row:
                            extracted_text += " | ".join(
                                str(cell) if cell else "" for cell in row
                            ) + "\n"
    except Exception as exc:
        return {"error": f"PDF text extraction failed: {exc}"}

    if not extracted_text.strip():
        return {"error": "No text extracted from PDF"}

    prompt = f"""Given this text extracted from an invoice, return only valid JSON.

TEXT:
{extracted_text}

Return exactly this JSON structure:
{{"customer_name": "bill-to company name", "invoice_id": "invoice number", "amount": total_amount_as_number, "issue_date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD", "payment_terms": "e.g. Net 30", "line_items": [{{"item": "description", "quantity": number, "unit_price": number, "total": number}}]}}"""

    try:
        return extract_json_object(prompt)
    except AzureOpenAIError as exc:
        return {"error": str(exc)}
