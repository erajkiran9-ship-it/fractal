from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.data_layer import excel_store as db

router = APIRouter(prefix="/api/collector", tags=["collector"])


class CallOutcome(BaseModel):
    customer_id: str
    invoice_id: str
    call_status: str  # connected, no_answer, voicemail
    outcome: str  # ptp, dispute, payment_confirmed, callback, refused, docs_needed, other
    ptp_amount: Optional[float] = None
    ptp_date: Optional[str] = None
    notes: str


@router.get("/tasks")
def get_call_tasks():
    """Get all pending call tasks for the collector."""
    activities = db.get_all_activities()
    # Filter for call_scheduled that haven't been completed
    pending_calls = []
    completed_call_invoices = set()

    for act in activities:
        if act.get("type") == "call_completed":
            completed_call_invoices.add(act.get("invoice_id"))

    for act in activities:
        if act.get("type") == "call_scheduled" and act.get("outcome") == "pending":
            if act.get("invoice_id") not in completed_call_invoices:
                # Get call script from communications
                comms = db.get_communications_by_invoice(act["invoice_id"])
                script = ""
                for comm in reversed(comms):
                    if comm.get("type") == "call_script":
                        script = comm.get("content", "")
                        break

                customer = db.get_customer(act["customer_id"])
                pending_calls.append({
                    "activity_id": act["activity_id"],
                    "customer_id": act["customer_id"],
                    "customer_name": customer["name"] if customer else act["customer_id"],
                    "invoice_id": act["invoice_id"],
                    "details": act.get("details", ""),
                    "date": str(act["date"]),
                    "script": script,
                })

    return {"tasks": pending_calls}


@router.get("/completed")
def get_completed_calls():
    """Get all completed call tasks."""
    activities = db.get_all_activities()
    completed = [
        act for act in activities
        if act.get("type") == "call_completed"
    ]
    return {"completed": completed}


@router.post("/outcome")
def submit_call_outcome(outcome: CallOutcome):
    """Collector logs the outcome of a call."""
    state = db.get_system_state()
    current_date = state.get("current_date", "2026-08-01")

    # Record the call activity
    activity_id = db.next_id("activities.xlsx", "activity_id", "ACT")
    details = f"Call status: {outcome.call_status}. Outcome: {outcome.outcome}."
    if outcome.notes:
        details += f" Notes: {outcome.notes}"

    db.add_activity({
        "activity_id": activity_id,
        "customer_id": outcome.customer_id,
        "invoice_id": outcome.invoice_id,
        "type": "call_completed",
        "date": current_date,
        "details": details,
        "outcome": outcome.outcome,
    })

    # Record call notes in communications
    comm_id = db.next_id("communications.xlsx", "comm_id", "COM")
    db.add_communication({
        "comm_id": comm_id,
        "customer_id": outcome.customer_id,
        "invoice_id": outcome.invoice_id,
        "direction": "inbound",
        "type": "call_notes",
        "date": current_date,
        "content": outcome.notes or f"Call outcome: {outcome.outcome}",
        "status": "received",
    })

    # If PTP was given, record it
    if outcome.outcome == "ptp" and outcome.ptp_amount and outcome.ptp_date:
        ptp_id = db.next_id("promises_to_pay.xlsx", "ptp_id", "PTP")
        db.add_ptp({
            "ptp_id": ptp_id,
            "customer_id": outcome.customer_id,
            "invoice_id": outcome.invoice_id,
            "amount": outcome.ptp_amount,
            "promise_date": outcome.ptp_date,
            "status": "ACTIVE",
            "created_date": current_date,
            "source": "call",
        })

    return {"status": "recorded", "activity_id": activity_id}
