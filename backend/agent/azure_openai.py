"""Small Azure OpenAI REST client shared by the agent and invoice parser."""

import json
from urllib.parse import quote

import requests

from backend.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    MAX_TOKENS,
)


class AzureOpenAIError(RuntimeError):
    """Raised when Azure OpenAI configuration or inference fails."""


def _chat_completions_url() -> str:
    deployment = quote(AZURE_OPENAI_DEPLOYMENT, safe="")
    return (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment}"
        "/chat/completions"
    )


def missing_configuration() -> list[str]:
    """List missing settings without exposing any credential value."""
    missing = []
    if not AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not AZURE_OPENAI_DEPLOYMENT:
        missing.append("AZURE_OPENAI_DEPLOYMENT")
    if not AZURE_OPENAI_API_VERSION:
        missing.append("AZURE_OPENAI_API_VERSION")
    if not AZURE_OPENAI_API_KEY:
        missing.append("AZURE_OPENAI_API_KEY")
    return missing


def _validate_configuration() -> None:
    missing = missing_configuration()
    if missing:
        raise AzureOpenAIError(
            f"Missing Azure OpenAI configuration: {', '.join(missing)}"
        )


def chat_completion(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    max_completion_tokens: int | None = None,
    timeout: int = 120,
) -> dict:
    """Create an Azure OpenAI chat completion using API-key authentication."""
    _validate_configuration()
    payload = {
        "messages": messages,
        "max_completion_tokens": max_completion_tokens or MAX_TOKENS,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        response = requests.post(
            _chat_completions_url(),
            params={"api-version": AZURE_OPENAI_API_VERSION},
            headers={
                "Content-Type": "application/json",
                "api-key": AZURE_OPENAI_API_KEY,
            },
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise AzureOpenAIError(f"Azure OpenAI request failed: {exc}") from exc

    if response.status_code >= 400:
        try:
            error_body = response.json()
            detail = error_body.get("error", {}).get("message") or str(error_body)
        except (ValueError, AttributeError):
            detail = response.text
        detail = " ".join(str(detail).split())[:500]
        raise AzureOpenAIError(
            f"Azure OpenAI API error {response.status_code}: {detail}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise AzureOpenAIError("Azure OpenAI returned invalid JSON") from exc


def response_message(result: dict) -> dict:
    """Return the first assistant message or raise a useful provider error."""
    choices = result.get("choices") or []
    if not choices:
        raise AzureOpenAIError("Azure OpenAI returned no completion choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise AzureOpenAIError("Azure OpenAI returned no assistant message")
    return message


def message_text(message: dict) -> str:
    """Normalize text-only and content-part assistant messages."""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                parts.append(str(item.get("text") or ""))
        return "\n".join(parts).strip()
    return ""


def extract_json_object(prompt: str, *, max_completion_tokens: int = 2000) -> dict:
    """Run a constrained extraction prompt and decode its JSON object response."""
    result = chat_completion(
        [
            {
                "role": "developer",
                "content": (
                    "Extract structured invoice fields. Return only one valid JSON "
                    "object with no Markdown or commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=max_completion_tokens,
        timeout=30,
    )
    text = message_text(response_message(result))
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:])
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AzureOpenAIError("Azure OpenAI returned invalid invoice JSON") from exc
    if not isinstance(parsed, dict):
        raise AzureOpenAIError("Azure OpenAI invoice response was not a JSON object")
    return parsed
