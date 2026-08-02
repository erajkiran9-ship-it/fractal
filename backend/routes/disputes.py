from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import BUSINESS_RULES
from backend.data_layer import excel_store as db
from backend.date_utils import parse_date

router = APIRouter(prefix="/api/disputes", tags=["disputes"])

OPEN_STATUSES = {"OPEN", "UNDER_REVIEW", "NEEDS_INFORMATION"}


class DisputeSubmission(BaseModel):
    customer_id: str
    invoice_id: str
    type: str
    amount: float = Field(gt=0)
    reason: str = Field(min_length=3)


class DisputeAssignment(BaseModel):
    owner: str = Field(min_length=2)


class DisputeInvestigation(BaseModel):
    notes: str = Field(min_length=2)
    investigator: str = "Dispute Team"


class DisputeResolution(BaseModel):
    decision: Literal[
        "accepted",
        "partially_accepted",
        "rejected",
        "more_information_required",
    ]
    approved_amount: Optional[float] = Field(default=None, ge=0)
    response: str = Field(min_length=3)
    notes: str = ""
    resolved_by: str = "Dispute Team"


def _current_date() -> str:
    return db.get_system_state().get("current_date", "2026-08-01")


def _outstanding(invoice: dict) -> float:
    return max(
        0.0,
        float(invoice.get("amount", 0) or 0)
        - float(invoice.get("amount_paid", 0) or 0),
    )


def _resume_invoice_status(invoice: dict, current_date: str) -> str:
    if _outstanding(invoice) <= 0:
        return "CLOSED"
    try:
        return (
            "OVERDUE"
            if parse_date(current_date) > parse_date(invoice["due_date"])
            else "OPEN"
        )
    except (KeyError, TypeError, ValueError):
        return "OPEN"


def _enrich_dispute(dispute: dict) -> dict:
    result = dict(dispute)
    customer = db.get_customer(dispute.get("customer_id", ""))
    invoice = db.get_invoice(dispute.get("invoice_id", ""))
    result["customer_name"] = customer.get("name") if customer else dispute.get("customer_id")
    result["invoice_amount"] = float(invoice.get("amount", 0) or 0) if invoice else 0
    result["amount_paid"] = float(invoice.get("amount_paid", 0) or 0) if invoice else 0
    result["outstanding_amount"] = _outstanding(invoice) if invoice else 0
    result["due_date"] = invoice.get("due_date") if invoice else None
    return result


def _record_activity(
    dispute: dict,
    activity_type: str,
    details: str,
    outcome: str,
    current_date: str,
) -> None:
    db.add_activity({
        "activity_id": db.next_id("activities.xlsx", "activity_id", "ACT"),
        "customer_id": dispute["customer_id"],
        "invoice_id": dispute["invoice_id"],
        "type": activity_type,
        "date": current_date,
        "details": details,
        "outcome": outcome,
    })


def _send_team_response(dispute: dict, response: str, current_date: str) -> None:
    db.add_communication({
        "comm_id": db.next_id("communications.xlsx", "comm_id", "COM"),
        "customer_id": dispute["customer_id"],
        "invoice_id": dispute["invoice_id"],
        "direction": "outbound",
        "type": "email",
        "date": current_date,
        "content": response,
        "status": "sent",
    })


def _merge_investigation_notes(
    dispute: dict,
    new_notes: str,
    author: str,
    current_date: str,
) -> str:
    existing = str(dispute.get("investigation_notes") or "").strip()
    addition = new_notes.strip()
    if not addition:
        return existing
    entry = f"[{current_date}] {author}: {addition}"
    return f"{existing}\n{entry}".strip()


def _update_workflow_after_resolution(
    dispute: dict,
    decision: str,
    remaining_balance: float,
    current_date: str,
) -> None:
    workflow = db.get_workflow_by_invoice(dispute["invoice_id"])
    if not workflow:
        return

    if decision == "more_information_required":
        status = "paused_dispute"
        reason_code = "DISPUTE_INFORMATION_REQUESTED"
        reasoning = (
            f"Dispute {dispute['dispute_id']} remains open. The dispute team requested "
            "additional information, so collection actions remain paused."
        )
    elif remaining_balance <= 0:
        status = "closed"
        reason_code = "DISPUTE_ACCEPTED_INVOICE_CLOSED"
        reasoning = (
            f"Dispute {dispute['dispute_id']} was accepted and cleared the remaining "
            "invoice balance. The collection workflow is closed."
        )
    else:
        status = "active_overdue"
        reason_code = "DISPUTE_RESOLVED_WORKFLOW_RESUMED"
        reasoning = (
            f"Dispute {dispute['dispute_id']} was resolved with decision "
            f"{decision}. Collection resumes for the remaining balance of "
            f"${remaining_balance:,.2f}."
        )

    db.update_workflow(dispute["invoice_id"], {
        "status": status,
        "reasoning": reasoning,
        "reason_code": reason_code,
        "last_updated": current_date,
    })


@router.get("")
def get_all_disputes():
    return {"disputes": [_enrich_dispute(item) for item in db.get_all_disputes()]}


@router.get("/queue")
def get_dispute_queue(include_resolved: bool = True):
    disputes = db.get_all_disputes()
    if not include_resolved:
        disputes = [item for item in disputes if item.get("status") in OPEN_STATUSES]
    disputes.sort(
        key=lambda item: (
            item.get("status") not in OPEN_STATUSES,
            str(item.get("created_date", "")),
        )
    )
    return {"disputes": [_enrich_dispute(item) for item in disputes]}


@router.get("/customer/{customer_id}")
def get_disputes_by_customer(customer_id: str):
    disputes = db.get_disputes_by_customer(customer_id)
    return {"disputes": [_enrich_dispute(item) for item in disputes]}


@router.get("/open")
def get_open_disputes():
    return {"disputes": [_enrich_dispute(item) for item in db.get_open_disputes()]}


@router.get("/{dispute_id}")
def get_dispute_detail(dispute_id: str):
    dispute = db.get_dispute(dispute_id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return {
        "dispute": _enrich_dispute(dispute),
        "customer": db.get_customer(dispute["customer_id"]),
        "invoice": db.get_invoice(dispute["invoice_id"]),
        "workflow": db.get_workflow_by_invoice(dispute["invoice_id"]),
        "communications": db.get_communications_by_invoice(dispute["invoice_id"]),
        "activities": db.get_activities_by_invoice(dispute["invoice_id"]),
    }


@router.post("")
def submit_dispute(dispute: DisputeSubmission):
    """Raise a dispute and immediately pause collection on its invoice."""
    invoice = db.get_invoice(dispute.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("customer_id") != dispute.customer_id:
        raise HTTPException(status_code=400, detail="Invoice does not belong to customer")
    if dispute.amount > _outstanding(invoice):
        raise HTTPException(
            status_code=400,
            detail="Disputed amount cannot exceed the outstanding invoice balance",
        )
    duplicate = next(
        (
            item
            for item in db.get_disputes_by_customer(dispute.customer_id)
            if item.get("invoice_id") == dispute.invoice_id
            and item.get("status") in OPEN_STATUSES
        ),
        None,
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"Active dispute {duplicate['dispute_id']} already exists",
        )

    current_date = _current_date()
    dispute_id = db.next_id("disputes.xlsx", "dispute_id", "DSP")
    owner = BUSINESS_RULES.get("dispute_routing", {}).get(
        dispute.type, "dispute_team"
    )
    dispute_record = {
        "dispute_id": dispute_id,
        "customer_id": dispute.customer_id,
        "invoice_id": dispute.invoice_id,
        "type": dispute.type,
        "amount": dispute.amount,
        "reason": dispute.reason,
        "status": "OPEN",
        "owner": owner,
        "created_date": current_date,
        "assigned_date": "",
        "investigation_notes": "",
        "decision": "",
        "approved_amount": 0,
        "team_response": "",
        "resolved_by": "",
        "resolved_date": "",
        "remaining_balance": _outstanding(invoice),
        "updated_date": current_date,
    }
    db.add_dispute(dispute_record)
    db.update_invoice(dispute.invoice_id, {"status": "DISPUTED"})

    workflow = db.get_workflow_by_invoice(dispute.invoice_id)
    if workflow:
        db.update_workflow(dispute.invoice_id, {
            "status": "paused_dispute",
            "reasoning": (
                f"Collection paused while dispute {dispute_id} is investigated by "
                f"{owner}. Disputed amount: ${dispute.amount:,.2f}."
            ),
            "reason_code": "DISPUTE_RAISED_WORKFLOW_PAUSED",
            "last_updated": current_date,
        })

    _record_activity(
        dispute_record,
        "dispute_raised",
        f"Dispute {dispute_id} raised for ${dispute.amount:,.2f}: {dispute.reason}",
        dispute_id,
        current_date,
    )
    return {"status": "filed", "dispute_id": dispute_id, "owner": owner}


@router.post("/{dispute_id}/assign")
def assign_dispute(dispute_id: str, assignment: DisputeAssignment):
    dispute = db.get_dispute(dispute_id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.get("status") not in OPEN_STATUSES:
        raise HTTPException(status_code=409, detail="Resolved dispute cannot be assigned")

    current_date = _current_date()
    db.update_dispute(dispute_id, {
        "owner": assignment.owner,
        "status": "UNDER_REVIEW",
        "assigned_date": current_date,
        "updated_date": current_date,
    })
    _record_activity(
        dispute,
        "dispute_assigned",
        f"Dispute {dispute_id} assigned to {assignment.owner}",
        "under_review",
        current_date,
    )
    return {"status": "assigned", "dispute_id": dispute_id, "owner": assignment.owner}


@router.post("/{dispute_id}/investigation")
def add_investigation_note(dispute_id: str, investigation: DisputeInvestigation):
    dispute = db.get_dispute(dispute_id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.get("status") not in OPEN_STATUSES:
        raise HTTPException(status_code=409, detail="Resolved dispute cannot be changed")

    current_date = _current_date()
    existing = str(dispute.get("investigation_notes") or "").strip()
    note = f"[{current_date}] {investigation.investigator}: {investigation.notes}"
    notes = f"{existing}\n{note}".strip()
    db.update_dispute(dispute_id, {
        "investigation_notes": notes,
        "status": "UNDER_REVIEW",
        "updated_date": current_date,
    })
    _record_activity(
        dispute,
        "dispute_investigated",
        note,
        "under_review",
        current_date,
    )
    return {"status": "noted", "dispute_id": dispute_id}


@router.post("/{dispute_id}/resolve")
def resolve_dispute(dispute_id: str, resolution: DisputeResolution):
    dispute = db.get_dispute(dispute_id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.get("status") not in OPEN_STATUSES:
        raise HTTPException(status_code=409, detail="Dispute is already resolved")
    invoice = db.get_invoice(dispute["invoice_id"])
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    current_date = _current_date()
    decision = resolution.decision
    disputed_amount = float(dispute.get("amount", 0) or 0)
    outstanding_before = _outstanding(invoice)

    if decision == "accepted":
        approved_amount = min(disputed_amount, outstanding_before)
    elif decision == "partially_accepted":
        if resolution.approved_amount is None or not (
            0 < resolution.approved_amount < disputed_amount
        ):
            raise HTTPException(
                status_code=400,
                detail="Partial acceptance requires an approved amount greater than zero and less than the disputed amount",
            )
        approved_amount = min(resolution.approved_amount, outstanding_before)
    else:
        approved_amount = 0.0

    if decision == "more_information_required":
        db.update_dispute(dispute_id, {
            "status": "NEEDS_INFORMATION",
            "investigation_notes": _merge_investigation_notes(
                dispute,
                resolution.notes,
                resolution.resolved_by,
                current_date,
            ),
            "decision": decision.upper(),
            "team_response": resolution.response,
            "resolved_by": resolution.resolved_by,
            "updated_date": current_date,
        })
        _send_team_response(dispute, resolution.response, current_date)
        _record_activity(
            dispute,
            "dispute_information_requested",
            f"Dispute team requested more information for {dispute_id}",
            dispute_id,
            current_date,
        )
        _update_workflow_after_resolution(
            dispute, decision, outstanding_before, current_date
        )
        return {
            "status": "needs_information",
            "dispute_id": dispute_id,
            "remaining_balance": outstanding_before,
        }

    new_invoice_amount = max(
        float(invoice.get("amount", 0) or 0) - approved_amount,
        float(invoice.get("amount_paid", 0) or 0),
    )
    adjusted_invoice = {**invoice, "amount": new_invoice_amount}
    remaining_balance = _outstanding(adjusted_invoice)
    invoice_status = _resume_invoice_status(adjusted_invoice, current_date)
    invoice_updates = {"status": invoice_status}
    if approved_amount > 0:
        invoice_updates["amount"] = new_invoice_amount
    db.update_invoice(dispute["invoice_id"], invoice_updates)

    updates = {
        "status": "RESOLVED",
        "decision": decision.upper(),
        "approved_amount": approved_amount,
        "team_response": resolution.response,
        "investigation_notes": _merge_investigation_notes(
            dispute,
            resolution.notes,
            resolution.resolved_by,
            current_date,
        ),
        "resolved_by": resolution.resolved_by,
        "resolved_date": current_date,
        "remaining_balance": remaining_balance,
        "updated_date": current_date,
    }
    db.update_dispute(dispute_id, updates)
    _send_team_response(dispute, resolution.response, current_date)
    _record_activity(
        dispute,
        "dispute_resolved",
        (
            f"Dispute {dispute_id} resolved as {decision}. Approved adjustment: "
            f"${approved_amount:,.2f}. Remaining balance: ${remaining_balance:,.2f}."
        ),
        dispute_id,
        current_date,
    )
    _update_workflow_after_resolution(
        dispute, decision, remaining_balance, current_date
    )

    return {
        "status": "resolved",
        "dispute_id": dispute_id,
        "decision": decision,
        "approved_amount": approved_amount,
        "remaining_balance": remaining_balance,
        "invoice_status": invoice_status,
    }
