"""
All tools available to the AI Collections Agent.
These use canonical JSON schemas and are implemented as Python functions.
"""

import os
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from backend.data_layer import excel_store as db
from backend.config import DATA_DIR
from backend.date_utils import parse_date
from backend.workflow_plan import (
    WorkflowPlanError,
    parse_workflow_plan,
    serialize_workflow_plan,
)

# ─────────────────────────────────────────────
# TOOL DEFINITIONS (Claude API format)
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "scan_incoming_invoices",
        "description": "Check the incoming invoices folder for new PDF files. Returns list of filenames found. Call this at the start of every daily cycle.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "parse_invoice_pdf",
        "description": "Extract structured data from an invoice PDF file. Returns customer name, invoice ID, amount, dates, and line items. Use this when a new PDF is found in the incoming folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The PDF filename to parse from data/incoming_invoices/"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "get_customer_profile",
        "description": "Get full customer profile including segment, credit limit, contacts, and hierarchy (parent/children). Use to understand who this customer is before making decisions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID (e.g., CUST-001) or customer name to search for"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_customer_history",
        "description": "Get complete historical data for a customer: all invoices, payments, PTPs (honored and broken), disputes, and collection activities. Essential for understanding payment patterns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID to get history for"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_open_invoices",
        "description": "Get all currently open/unpaid invoices across all customers with aging information.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_new_events",
        "description": "Check for new events since the last cycle: new payments, new inbound messages/replies, new disputes, new call outcomes from collectors, PTP deadlines that have passed. Call this to detect what has changed.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_current_workflow",
        "description": "Get the current workflow plan for a specific invoice, including status, scheduled actions, completed actions, reasoning, and confidence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "string",
                    "description": "Invoice ID to get workflow for"
                }
            },
            "required": ["invoice_id"]
        }
    },
    {
        "name": "get_credit_exposure",
        "description": "Get credit utilization for a customer: limit, current exposure, available credit, percentage used, and status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID to check credit for"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "send_email",
        "description": "Send a collection email to a customer. Saves the email as a .txt file and records it in the communications log. Use for reminders, demands, confirmations, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID"},
                "invoice_id": {"type": "string", "description": "Related invoice ID"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Full email body text"},
                "tone": {"type": "string", "enum": ["soft", "moderate", "firm", "aggressive"], "description": "Tone of the email"},
                "documents_attached": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of document types attached (e.g., invoice_pdf, pod, statement)"
                }
            },
            "required": ["customer_id", "invoice_id", "subject", "body", "tone"]
        }
    },
    {
        "name": "create_call_task",
        "description": "Create a call task for the human collector with a generated script. The task will appear on the Collector Dashboard.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID to call"},
                "invoice_id": {"type": "string", "description": "Related invoice ID"},
                "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"], "description": "Call priority"},
                "reason": {"type": "string", "description": "Why this call is needed"},
                "script": {"type": "string", "description": "Full call script with context, suggested opening, and handling scenarios"}
            },
            "required": ["customer_id", "invoice_id", "priority", "reason", "script"]
        }
    },
    {
        "name": "log_promise_to_pay",
        "description": "Record a new promise-to-pay from a customer. Creates a PTP record for monitoring.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "invoice_id": {"type": "string"},
                "amount": {"type": "number", "description": "Amount promised"},
                "promise_date": {"type": "string", "description": "Date promised (YYYY-MM-DD)"},
                "source": {"type": "string", "description": "How PTP was received: email, call, portal"}
            },
            "required": ["customer_id", "invoice_id", "amount", "promise_date", "source"]
        }
    },
    {
        "name": "mark_ptp_broken",
        "description": "Mark a promise-to-pay as broken when the deadline passes without payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ptp_id": {"type": "string", "description": "PTP ID to mark as broken"},
                "reason": {"type": "string", "description": "Why it's broken (e.g., deadline passed, no payment)"}
            },
            "required": ["ptp_id", "reason"]
        }
    },
    {
        "name": "mark_ptp_honored",
        "description": "Mark a promise-to-pay as honored when payment is received on or before the deadline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ptp_id": {"type": "string", "description": "PTP ID to mark as honored"}
            },
            "required": ["ptp_id"]
        }
    },
    {
        "name": "escalate",
        "description": "Escalate an invoice to a higher authority (manager, credit team, sales, legal).",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "invoice_id": {"type": "string"},
                "escalate_to": {"type": "string", "description": "Who to escalate to: collections_manager, credit_team, relationship_manager, sales_vp, legal"},
                "reason": {"type": "string", "description": "Detailed reason for escalation"},
                "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"]}
            },
            "required": ["customer_id", "invoice_id", "escalate_to", "reason", "priority"]
        }
    },
    {
        "name": "route_dispute",
        "description": "Route a dispute or trade deduction to the appropriate team for resolution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dispute_id": {"type": "string"},
                "route_to": {"type": "string", "description": "Team to route to: dispute_team, trade_team, operations_team, finance_team"},
                "reason": {"type": "string", "description": "Why routing to this team"}
            },
            "required": ["dispute_id", "route_to", "reason"]
        }
    },
    {
        "name": "update_workflow",
        "description": "Save or update the workflow plan for an invoice. Use this to record your decisions, reasoning, scheduled actions, and confidence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string"},
                "customer_id": {"type": "string"},
                "status": {"type": "string", "description": "Workflow status: active, active_overdue, active_ptp_monitoring, active_escalated, paused_dispute, paused_document, closed"},
                "plan": {"type": "object", "description": "The full workflow plan with scheduled_actions, completed_actions, cancelled_actions, contingencies, flags"},
                "reasoning": {"type": "string", "description": "Your detailed reasoning for this decision"},
                "confidence": {"type": "integer", "description": "Confidence level 0-100"},
                "reason_code": {"type": "string", "description": "Reason code from the defined list"}
            },
            "required": ["invoice_id", "customer_id", "status", "plan", "reasoning", "confidence", "reason_code"]
        }
    },
    {
        "name": "update_invoice_status",
        "description": "Register a newly parsed invoice or update an existing invoice's status. For a new invoice, pass customer_id, amount, issue_date, due_date, and filename from the parsed PDF result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string"},
                "customer_id": {"type": "string", "description": "Resolved customer ID; required when registering a new invoice"},
                "amount": {"type": "number", "description": "Invoice total; required when registering a new invoice"},
                "issue_date": {"type": "string", "description": "Invoice issue date (YYYY-MM-DD); required when registering a new invoice"},
                "due_date": {"type": "string", "description": "Invoice due date (YYYY-MM-DD); required when registering a new invoice"},
                "filename": {"type": "string", "description": "Original PDF filename from _filename; required to archive a newly registered invoice"},
                "status": {"type": "string", "description": "New status: OPEN, OVERDUE, PARTIAL_PAID, PAID, DISPUTED, CLOSED"},
                "amount_paid": {"type": "number", "description": "Total amount paid so far"},
                "paid_date": {"type": "string", "description": "Date of payment (YYYY-MM-DD)"}
            },
            "required": ["invoice_id", "status"]
        }
    },
    {
        "name": "update_credit_exposure",
        "description": "Update credit exposure for a customer (e.g., when new invoice added or payment received).",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "new_exposure": {"type": "number", "description": "New total exposure amount"},
                "reason": {"type": "string", "description": "Why exposure changed"}
            },
            "required": ["customer_id", "new_exposure", "reason"]
        }
    },
    {
        "name": "record_activity",
        "description": "Log any activity or action taken. All actions should be logged for audit trail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "invoice_id": {"type": "string"},
                "type": {"type": "string", "description": "Activity type: email_sent, call_scheduled, call_completed, escalation, ptp_logged, ptp_broken, ptp_honored, dispute_raised, dispute_routed, document_requested, payment_received, workflow_created, workflow_modified, workflow_closed, credit_alert, credit_hold"},
                "details": {"type": "string", "description": "Detailed description of the activity"},
                "outcome": {"type": "string", "description": "Outcome or result of the activity"}
            },
            "required": ["customer_id", "invoice_id", "type", "details"]
        }
    },
    {
        "name": "attach_document",
        "description": "Recommend or note a supporting document to attach to a communication.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string"},
                "doc_type": {"type": "string", "description": "Document type: invoice_pdf, pod, statement, remittance, promo_agreement"},
                "reason": {"type": "string", "description": "Why this document should be attached"}
            },
            "required": ["invoice_id", "doc_type", "reason"]
        }
    },
]


# ─────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# ─────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict, current_date: str) -> str:
    """Execute a tool and return the result as a string."""
    try:
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        result = handler(tool_input, current_date)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _handle_scan_incoming_invoices(input: dict, current_date: str) -> dict:
    files = db.scan_incoming_invoices()
    return {"files_found": files, "count": len(files)}


def _handle_parse_invoice_pdf(input: dict, current_date: str) -> dict:
    import pdfplumber
    from backend.agent.azure_openai import AzureOpenAIError, extract_json_object

    filename = input["filename"]
    filepath = DATA_DIR / "incoming_invoices" / filename

    if not filepath.exists():
        return {"error": f"File not found: {filename}"}

    # Step 1: Extract text from PDF using pdfplumber (NOT LLM)
    extracted_text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"

                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            extracted_text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
    except Exception as e:
        return {"error": f"Failed to extract text from PDF: {str(e)}"}

    if not extracted_text.strip():
        return {"error": "No text could be extracted from PDF"}

    # Step 2: Use Azure OpenAI for structured field extraction
    prompt = f"""Given this text extracted from an invoice PDF, extract the structured data.
Return ONLY valid JSON with no extra text.

EXTRACTED TEXT:
---
{extracted_text}
---

Return this exact JSON structure:
{{
    "customer_name": "the company/customer being billed (Bill To)",
    "invoice_id": "invoice number/ID",
    "amount": total amount as a number (no $ sign or commas),
    "issue_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "payment_terms": "e.g. Net 30",
    "line_items": [{{"item": "description", "quantity": number, "unit_price": number, "total": number}}]
}}"""

    try:
        parsed = extract_json_object(prompt)
        parsed["_source_text"] = extracted_text[:500]
        parsed["_filename"] = filename
        return parsed

    except (AzureOpenAIError, ValueError) as e:
        return {
            "error": f"Failed to parse extracted text: {str(e)}",
            "extracted_text": extracted_text[:1000],
            "filename": filename
        }


def _handle_get_customer_profile(input: dict, current_date: str) -> dict:
    customer_id = input["customer_id"]
    customer = db.get_customer(customer_id)
    if not customer:
        customer = db.get_customer_by_name(customer_id)
    if not customer:
        return {"error": f"Customer not found: {customer_id}"}

    actual_id = customer["customer_id"]
    hierarchy = db.get_customer_hierarchy(actual_id)

    return {
        "customer": customer,
        "hierarchy": hierarchy
    }


def _handle_get_customer_history(input: dict, current_date: str) -> dict:
    customer_id = input["customer_id"]

    invoices = db.get_invoices_by_customer(customer_id)
    payments = db.get_payments_by_customer(customer_id)
    ptps = db.get_ptps_by_customer(customer_id)
    disputes = db.get_disputes_by_customer(customer_id)
    activities = db.get_activities_by_customer(customer_id)
    communications = db.get_communications_by_customer(customer_id)

    # Also check parent-level data
    customer = db.get_customer(customer_id)
    parent_id = customer.get("parent_customer_id") if customer else None
    if parent_id and str(parent_id) != "nan":
        parent_invoices = db.get_invoices_by_customer(parent_id)
        parent_ptps = db.get_ptps_by_customer(parent_id)
        invoices.extend(parent_invoices)
        ptps.extend(parent_ptps)

    # Calculate stats
    paid_invoices = [inv for inv in invoices if inv.get("status") == "CLOSED" and inv.get("paid_date")]
    days_late_list = []
    for inv in paid_invoices:
        try:
            due = parse_date(inv["due_date"])
            paid = parse_date(inv["paid_date"])
            days_late = (paid - due).days
            if days_late > 0:
                days_late_list.append(days_late)
        except:
            pass

    broken_ptps = [p for p in ptps if p.get("status") == "BROKEN"]
    honored_ptps = [p for p in ptps if p.get("status") == "HONORED"]

    return {
        "invoices": invoices,
        "payments": payments,
        "promises_to_pay": ptps,
        "disputes": disputes,
        "activities": activities[-20:],  # Last 20 activities
        "communications": communications[-10:],  # Last 10 comms
        "stats": {
            "total_invoices": len(invoices),
            "avg_days_late": round(sum(days_late_list) / len(days_late_list), 1) if days_late_list else 0,
            "max_days_late": max(days_late_list) if days_late_list else 0,
            "broken_ptps": len(broken_ptps),
            "honored_ptps": len(honored_ptps),
            "open_disputes": len([d for d in disputes if d.get("status") in ["OPEN", "UNDER_REVIEW"]]),
        }
    }


def _handle_get_open_invoices(input: dict, current_date: str) -> dict:
    invoices = db.get_open_invoices()
    results = []
    today = parse_date(current_date)
    for inv in invoices:
        due_date = parse_date(inv["due_date"])
        days_overdue = (today - due_date).days
        aging_bucket = "current"
        if days_overdue > 90:
            aging_bucket = "90+"
        elif days_overdue > 60:
            aging_bucket = "61-90"
        elif days_overdue > 30:
            aging_bucket = "31-60"
        elif days_overdue > 0:
            aging_bucket = "1-30"

        inv["days_overdue"] = days_overdue
        inv["aging_bucket"] = aging_bucket
        results.append(inv)

    return {"open_invoices": results, "count": len(results)}


def _handle_get_new_events(input: dict, current_date: str) -> dict:
    state = db.get_system_state()
    last_cycle = state.get("last_cycle_date") or "2026-01-01"

    events = []

    # Check new payments
    new_payments = db.get_new_payments_since(last_cycle)
    for p in new_payments:
        events.append({
            "type": "payment_received",
            "customer_id": p["customer_id"],
            "invoice_id": p["invoice_id"],
            "amount": p["amount"],
            "date": str(p["date"]),
            "details": f"Payment of ${p['amount']:,.2f} received"
        })

    # Check new inbound communications
    new_messages = db.get_new_inbound_since(last_cycle)
    for msg in new_messages:
        events.append({
            "type": "message_inbound",
            "customer_id": msg["customer_id"],
            "invoice_id": msg["invoice_id"],
            "content": msg["content"],
            "date": str(msg["date"]),
            "comm_type": msg.get("type", "email"),
            "details": f"New {msg.get('type', 'message')} from customer"
        })

    # Check new activities (call outcomes from collector)
    new_activities = db.get_new_activities_since(last_cycle)
    for act in new_activities:
        if act.get("type") == "call_completed":
            events.append({
                "type": "call_outcome",
                "customer_id": act["customer_id"],
                "invoice_id": act["invoice_id"],
                "details": act.get("details", ""),
                "outcome": act.get("outcome", ""),
                "date": str(act["date"])
            })
        elif act.get("type") in {
            "dispute_raised",
            "dispute_information_requested",
            "dispute_resolved",
        }:
            dispute_id = str(act.get("outcome") or "")
            dispute = db.get_dispute(dispute_id) if dispute_id else None
            event_type = {
                "dispute_raised": "dispute_raised",
                "dispute_information_requested": "dispute_information_requested",
                "dispute_resolved": "dispute_resolved",
            }[act["type"]]
            events.append({
                "type": event_type,
                "dispute_id": dispute_id,
                "customer_id": act["customer_id"],
                "invoice_id": act["invoice_id"],
                "status": dispute.get("status") if dispute else "",
                "decision": dispute.get("decision") if dispute else "",
                "disputed_amount": dispute.get("amount") if dispute else 0,
                "approved_amount": dispute.get("approved_amount") if dispute else 0,
                "remaining_balance": dispute.get("remaining_balance") if dispute else None,
                "team_response": dispute.get("team_response") if dispute else "",
                "details": act.get("details", ""),
                "date": str(act["date"]),
            })

    # Check PTP deadlines
    active_ptps = db.get_active_ptps()
    today = parse_date(current_date)
    for ptp in active_ptps:
        promise_date = parse_date(ptp["promise_date"])
        grace_days = 1  # from rules
        if today > promise_date + timedelta(days=grace_days):
            # Check if payment was received
            payments = db.get_payments_by_invoice(ptp["invoice_id"])
            paid_after_ptp = any(
                parse_date(p["date"]) >= promise_date
                for p in payments
            )
            if not paid_after_ptp:
                events.append({
                    "type": "ptp_deadline_passed",
                    "customer_id": ptp["customer_id"],
                    "invoice_id": ptp["invoice_id"],
                    "ptp_id": ptp["ptp_id"],
                    "promise_date": str(ptp["promise_date"]),
                    "amount": ptp["amount"],
                    "details": f"PTP deadline {ptp['promise_date']} passed with no payment"
                })

    # Check credit thresholds
    all_credit = db.get_all_credit_exposure()
    for credit in all_credit:
        pct = credit.get("percentage_used", 0)
        if pct >= 80 and credit.get("status") != "HOLD":
            events.append({
                "type": "credit_threshold_warning",
                "customer_id": credit["customer_id"],
                "percentage_used": pct,
                "details": f"Credit utilization at {pct:.0f}%"
            })

    return {"events": events, "count": len(events)}


def _handle_get_current_workflow(input: dict, current_date: str) -> dict:
    invoice_id = input["invoice_id"]
    workflow = db.get_workflow_by_invoice(invoice_id)
    if not workflow:
        return {"status": "no_workflow", "invoice_id": invoice_id}

    try:
        workflow["plan"] = parse_workflow_plan(workflow.get("plan_json", {}))
    except WorkflowPlanError:
        workflow["plan"] = {}

    return workflow


def _handle_get_credit_exposure(input: dict, current_date: str) -> dict:
    customer_id = input["customer_id"]
    credit = db.get_credit_exposure(customer_id)
    if not credit:
        return {"error": f"No credit data for: {customer_id}"}
    return credit


def _handle_send_email(input: dict, current_date: str) -> dict:
    customer_id = input["customer_id"]
    invoice_id = input["invoice_id"]
    subject = input["subject"]
    body = input["body"]
    tone = input.get("tone", "moderate")
    docs = input.get("documents_attached", [])

    customer = db.get_customer(customer_id)
    customer_name = customer["name"] if customer else customer_id

    # Save email as .txt file
    safe_name = customer_name.replace(" ", "_")
    filename = f"{current_date}_{safe_name}_{invoice_id}_{tone}.txt"
    email_path = DATA_DIR / "emails" / filename

    email_content = f"To: {customer.get('contact_email', 'N/A')}\n"
    email_content += f"From: collections@nutricorp.com\n"
    email_content += f"Date: {current_date}\n"
    email_content += f"Subject: {subject}\n"
    email_content += f"Documents Attached: {', '.join(docs) if docs else 'None'}\n"
    email_content += f"\n{'='*60}\n\n"
    email_content += body

    with open(email_path, "w") as f:
        f.write(email_content)

    # Record in communications
    comm_id = db.next_id("communications.xlsx", "comm_id", "COM")
    db.add_communication({
        "comm_id": comm_id,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "direction": "outbound",
        "type": "email",
        "date": current_date,
        "content": body,
        "status": "sent"
    })

    return {
        "status": "sent",
        "file": str(email_path),
        "comm_id": comm_id,
        "tone": tone,
        "documents_attached": docs
    }


def _handle_create_call_task(input: dict, current_date: str) -> dict:
    customer_id = input["customer_id"]
    invoice_id = input["invoice_id"]
    priority = input["priority"]
    reason = input["reason"]
    script = input["script"]

    # Record activity
    activity_id = db.next_id("activities.xlsx", "activity_id", "ACT")
    db.add_activity({
        "activity_id": activity_id,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "type": "call_scheduled",
        "date": current_date,
        "details": f"Call task created. Priority: {priority}. Reason: {reason}",
        "outcome": "pending"
    })

    # Save call script as .txt
    customer = db.get_customer(customer_id)
    customer_name = customer["name"] if customer else customer_id
    safe_name = customer_name.replace(" ", "_")
    script_path = DATA_DIR / "emails" / f"{current_date}_{safe_name}_{invoice_id}_call_script.txt"

    with open(script_path, "w") as f:
        f.write(f"CALL SCRIPT\n{'='*60}\n")
        f.write(f"Customer: {customer_name}\n")
        f.write(f"Invoice: {invoice_id}\n")
        f.write(f"Priority: {priority}\n")
        f.write(f"Reason: {reason}\n")
        f.write(f"Date: {current_date}\n")
        f.write(f"\n{'='*60}\n\n")
        f.write(script)

    # Record in communications
    comm_id = db.next_id("communications.xlsx", "comm_id", "COM")
    db.add_communication({
        "comm_id": comm_id,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "direction": "outbound",
        "type": "call_script",
        "date": current_date,
        "content": script,
        "status": "pending"
    })

    return {
        "status": "created",
        "activity_id": activity_id,
        "priority": priority,
        "script_file": str(script_path)
    }


def _handle_log_promise_to_pay(input: dict, current_date: str) -> dict:
    ptp_id = db.next_id("promises_to_pay.xlsx", "ptp_id", "PTP")
    ptp = {
        "ptp_id": ptp_id,
        "customer_id": input["customer_id"],
        "invoice_id": input["invoice_id"],
        "amount": input["amount"],
        "promise_date": input["promise_date"],
        "status": "ACTIVE",
        "created_date": current_date,
        "source": input.get("source", "email")
    }
    db.add_ptp(ptp)
    return {"status": "logged", "ptp_id": ptp_id, **ptp}


def _handle_mark_ptp_broken(input: dict, current_date: str) -> dict:
    ptp_id = input["ptp_id"]
    reason = input["reason"]
    db.update_ptp(ptp_id, {"status": "BROKEN"})

    # Get PTP details for activity log
    ptps = db.get_all_ptps()
    ptp = next((p for p in ptps if p["ptp_id"] == ptp_id), None)

    if ptp:
        activity_id = db.next_id("activities.xlsx", "activity_id", "ACT")
        db.add_activity({
            "activity_id": activity_id,
            "customer_id": ptp["customer_id"],
            "invoice_id": ptp["invoice_id"],
            "type": "ptp_broken",
            "date": current_date,
            "details": f"PTP {ptp_id} marked BROKEN. {reason}",
            "outcome": "escalation_required"
        })

    return {"status": "marked_broken", "ptp_id": ptp_id, "reason": reason}


def _handle_mark_ptp_honored(input: dict, current_date: str) -> dict:
    ptp_id = input["ptp_id"]
    db.update_ptp(ptp_id, {"status": "HONORED"})
    return {"status": "marked_honored", "ptp_id": ptp_id}


def _handle_escalate(input: dict, current_date: str) -> dict:
    activity_id = db.next_id("activities.xlsx", "activity_id", "ACT")
    db.add_activity({
        "activity_id": activity_id,
        "customer_id": input["customer_id"],
        "invoice_id": input["invoice_id"],
        "type": "escalation",
        "date": current_date,
        "details": f"Escalated to {input['escalate_to']}. Priority: {input['priority']}. Reason: {input['reason']}",
        "outcome": "pending"
    })
    return {
        "status": "escalated",
        "escalate_to": input["escalate_to"],
        "priority": input["priority"],
        "activity_id": activity_id
    }


def _handle_route_dispute(input: dict, current_date: str) -> dict:
    dispute_id = input["dispute_id"]
    route_to = input["route_to"]
    db.update_dispute(dispute_id, {"owner": route_to, "status": "UNDER_REVIEW"})

    activity_id = db.next_id("activities.xlsx", "activity_id", "ACT")
    dispute = next((d for d in db.get_all_disputes() if d["dispute_id"] == dispute_id), {})
    db.add_activity({
        "activity_id": activity_id,
        "customer_id": dispute.get("customer_id", ""),
        "invoice_id": dispute.get("invoice_id", ""),
        "type": "dispute_routed",
        "date": current_date,
        "details": f"Dispute {dispute_id} routed to {route_to}. {input['reason']}",
        "outcome": "under_review"
    })
    return {"status": "routed", "dispute_id": dispute_id, "route_to": route_to}


def _handle_update_workflow(input: dict, current_date: str) -> dict:
    invoice_id = input["invoice_id"]
    customer_id = input["customer_id"]
    existing = db.get_workflow_by_invoice(invoice_id)

    try:
        plan_json = serialize_workflow_plan(input.get("plan", {}))
    except WorkflowPlanError as exc:
        return {"error": str(exc), "invoice_id": invoice_id}
    workflow_data = {
        "status": input["status"],
        "plan_json": plan_json,
        "reasoning": input["reasoning"],
        "confidence": input["confidence"],
        "reason_code": input["reason_code"],
        "last_updated": current_date,
    }

    if existing:
        db.update_workflow(invoice_id, workflow_data)
    else:
        workflow_id = db.next_id("workflow_states.xlsx", "workflow_id", "WF")
        workflow_data["workflow_id"] = workflow_id
        workflow_data["invoice_id"] = invoice_id
        workflow_data["customer_id"] = customer_id
        db.add_workflow(workflow_data)

    return {"status": "saved", "invoice_id": invoice_id}


def _handle_update_invoice_status(input: dict, current_date: str) -> dict:
    invoice_id = input["invoice_id"]
    updates = {"status": input["status"]}
    if "amount_paid" in input:
        updates["amount_paid"] = input["amount_paid"]
    if "paid_date" in input:
        updates["paid_date"] = input["paid_date"]

    # Check if this is a new invoice being registered
    existing = db.get_invoice(invoice_id)
    if not existing:
        # This is a new invoice from PDF parsing
        new_invoice = {
            "invoice_id": invoice_id,
            "customer_id": input.get("customer_id", ""),
            "amount": input.get("amount", 0),
            "issue_date": input.get("issue_date", current_date),
            "due_date": input.get("due_date", ""),
            "status": input["status"],
            "amount_paid": input.get("amount_paid", 0),
            "paid_date": input.get("paid_date", None),
        }
        db.add_invoice(new_invoice)
        db.move_processed_invoice(input.get("filename", ""))
        return {"status": "created", "invoice_id": invoice_id}

    db.update_invoice(invoice_id, updates)
    return {"status": "updated", "invoice_id": invoice_id, "new_status": input["status"]}


def _handle_update_credit_exposure(input: dict, current_date: str) -> dict:
    customer_id = input["customer_id"]
    new_exposure = input["new_exposure"]

    credit = db.get_credit_exposure(customer_id)
    if not credit:
        return {"error": f"No credit data for {customer_id}"}

    limit = credit["credit_limit"]
    available = limit - new_exposure
    pct = (new_exposure / limit * 100) if limit > 0 else 0

    status = "HEALTHY"
    if pct >= 100:
        status = "HOLD"
    elif pct >= 95:
        status = "CRITICAL"
    elif pct >= 80:
        status = "WARNING"

    db.update_credit_exposure(customer_id, {
        "current_exposure": new_exposure,
        "available_credit": available,
        "percentage_used": round(pct, 1),
        "status": status
    })

    return {
        "status": "updated",
        "customer_id": customer_id,
        "new_exposure": new_exposure,
        "percentage_used": round(pct, 1),
        "credit_status": status
    }


def _handle_record_activity(input: dict, current_date: str) -> dict:
    activity_id = db.next_id("activities.xlsx", "activity_id", "ACT")
    activity = {
        "activity_id": activity_id,
        "customer_id": input["customer_id"],
        "invoice_id": input["invoice_id"],
        "type": input["type"],
        "date": current_date,
        "details": input["details"],
        "outcome": input.get("outcome", "")
    }
    db.add_activity(activity)
    return {"status": "recorded", "activity_id": activity_id}


def _handle_attach_document(input: dict, current_date: str) -> dict:
    invoice_id = input["invoice_id"]
    doc_type = input["doc_type"]
    docs = db.get_documents_by_invoice(invoice_id)
    matching = [d for d in docs if d.get("doc_type") == doc_type]

    if matching:
        return {
            "status": "found",
            "doc_type": doc_type,
            "file_path": matching[0]["file_path"],
            "reason": input["reason"]
        }
    return {
        "status": "recommended",
        "doc_type": doc_type,
        "reason": input["reason"],
        "note": "Document not in system yet — requesting from operations"
    }


# ─────────────────────────────────────────────
# TOOL HANDLER MAP
# ─────────────────────────────────────────────

TOOL_HANDLERS = {
    "scan_incoming_invoices": _handle_scan_incoming_invoices,
    "parse_invoice_pdf": _handle_parse_invoice_pdf,
    "get_customer_profile": _handle_get_customer_profile,
    "get_customer_history": _handle_get_customer_history,
    "get_open_invoices": _handle_get_open_invoices,
    "get_new_events": _handle_get_new_events,
    "get_current_workflow": _handle_get_current_workflow,
    "get_credit_exposure": _handle_get_credit_exposure,
    "send_email": _handle_send_email,
    "create_call_task": _handle_create_call_task,
    "log_promise_to_pay": _handle_log_promise_to_pay,
    "mark_ptp_broken": _handle_mark_ptp_broken,
    "mark_ptp_honored": _handle_mark_ptp_honored,
    "escalate": _handle_escalate,
    "route_dispute": _handle_route_dispute,
    "update_workflow": _handle_update_workflow,
    "update_invoice_status": _handle_update_invoice_status,
    "update_credit_exposure": _handle_update_credit_exposure,
    "record_activity": _handle_record_activity,
    "attach_document": _handle_attach_document,
}
