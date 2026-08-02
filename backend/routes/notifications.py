"""Date-scoped notification feeds for the role landing dashboards."""

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException

from backend.data_layer import excel_store as db
from backend.date_utils import parse_date


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


DISPUTE_ACTIVITY_TITLES = {
    "dispute_raised": "New dispute received",
    "dispute_routed": "Dispute routed",
    "dispute_assigned": "Dispute assigned",
    "dispute_investigated": "Investigation updated",
    "dispute_information_requested": "Information requested",
    "dispute_resolved": "Dispute resolved",
}

COLLECTOR_ACTIVITY_TITLES = {
    "call_scheduled": "New call task",
    "call_completed": "Call outcome recorded",
    "ptp_broken": "Promise to pay broken",
    "ptp_honored": "Promise to pay honored",
    "document_requested": "Documents required",
    "dispute_raised": "Customer raised a dispute",
}

CUSTOMER_DISPUTE_TITLES = {
    "dispute_raised": "Dispute submitted",
    "dispute_information_requested": "More information required",
    "dispute_resolved": "Dispute decision available",
}


def _current_date(requested_date: str | None) -> str:
    value = requested_date or db.get_system_state().get("current_date", "2026-08-01")
    try:
        return parse_date(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Date must use YYYY-MM-DD format")


def _date_string(value: object) -> str:
    try:
        return parse_date(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return str(value).split(" ", 1)[0]


def _on_date(record: dict, field: str, current_date: str) -> bool:
    value = record.get(field)
    return bool(value) and _date_string(value) == current_date


def _customer_name(customer_id: str) -> str:
    customer = db.get_customer(customer_id)
    return str(customer.get("name")) if customer else customer_id


def _summary(value: object, fallback: str) -> str:
    text = " ".join(str(value or fallback).split())
    return text if len(text) <= 180 else f"{text[:177]}..."


def _matching_dispute(activity: dict) -> dict | None:
    outcome = str(activity.get("outcome") or "")
    if outcome.startswith("DSP-"):
        dispute = db.get_dispute(outcome)
        if dispute:
            return dispute

    matches = [
        dispute
        for dispute in db.get_all_disputes()
        if dispute.get("customer_id") == activity.get("customer_id")
        and dispute.get("invoice_id") == activity.get("invoice_id")
    ]
    if not matches:
        return None
    matches.sort(
        key=lambda dispute: str(
            dispute.get("updated_date") or dispute.get("created_date") or ""
        ),
        reverse=True,
    )
    return matches[0]


def _notification(
    *,
    notification_id: str,
    event_type: str,
    title: str,
    message: str,
    date: str,
    customer_id: str,
    invoice_id: str = "",
    dispute_id: str = "",
    activity_id: str = "",
    status: str = "",
    severity: str = "info",
    action_required: bool = False,
    target_url: str,
) -> dict:
    return {
        "notification_id": notification_id,
        "event_type": event_type,
        "title": title,
        "message": _summary(message, title),
        "date": date,
        "customer_id": customer_id,
        "customer_name": _customer_name(customer_id),
        "invoice_id": invoice_id,
        "dispute_id": dispute_id,
        "activity_id": activity_id,
        "status": status,
        "severity": severity,
        "action_required": action_required,
        "target_url": target_url,
    }


def _response(role: str, date: str, notifications: list[dict]) -> dict:
    notifications.reverse()
    return {
        "role": role,
        "date": date,
        "count": len(notifications),
        "notifications": notifications,
    }


@router.get("/disputes")
def get_dispute_notifications(date: str | None = None):
    current_date = _current_date(date)
    notifications = []
    represented_disputes = set()

    for activity in db.get_all_activities():
        activity_type = str(activity.get("type") or "")
        if activity_type not in DISPUTE_ACTIVITY_TITLES or not _on_date(
            activity, "date", current_date
        ):
            continue
        dispute = _matching_dispute(activity)
        dispute_id = str(dispute.get("dispute_id") or "") if dispute else ""
        if activity_type == "dispute_raised" and dispute_id:
            represented_disputes.add(dispute_id)
        status = str(dispute.get("status") or "") if dispute else ""
        severity = (
            "success"
            if activity_type == "dispute_resolved"
            else "warning"
            if activity_type in {"dispute_raised", "dispute_information_requested"}
            else "info"
        )
        target = (
            f"/disputes/case/{dispute_id}"
            if dispute_id
            else "/disputes/workbench"
        )
        notifications.append(
            _notification(
                notification_id=f"dispute-activity:{activity.get('activity_id')}",
                event_type=activity_type,
                title=DISPUTE_ACTIVITY_TITLES[activity_type],
                message=activity.get("details") or DISPUTE_ACTIVITY_TITLES[activity_type],
                date=current_date,
                customer_id=str(activity.get("customer_id") or ""),
                invoice_id=str(activity.get("invoice_id") or ""),
                dispute_id=dispute_id,
                activity_id=str(activity.get("activity_id") or ""),
                status=status,
                severity=severity,
                action_required=status in {"OPEN", "UNDER_REVIEW", "NEEDS_INFORMATION"},
                target_url=target,
            )
        )

    # Legacy/seed disputes may not have a corresponding dispute_raised activity.
    for dispute in db.get_all_disputes():
        dispute_id = str(dispute.get("dispute_id") or "")
        if dispute_id in represented_disputes or not _on_date(
            dispute, "created_date", current_date
        ):
            continue
        notifications.append(
            _notification(
                notification_id=f"dispute-created:{dispute_id}",
                event_type="dispute_raised",
                title="New dispute received",
                message=dispute.get("reason") or "A customer raised a new dispute.",
                date=current_date,
                customer_id=str(dispute.get("customer_id") or ""),
                invoice_id=str(dispute.get("invoice_id") or ""),
                dispute_id=dispute_id,
                status=str(dispute.get("status") or ""),
                severity="warning",
                action_required=str(dispute.get("status") or "") != "RESOLVED",
                target_url=f"/disputes/case/{dispute_id}",
            )
        )

    return _response("disputes", current_date, notifications)


def _collector_target(activity_id: str, invoice_id: str) -> str:
    query = urlencode(
        {key: value for key, value in {"taskId": activity_id, "invoiceId": invoice_id}.items() if value}
    )
    return f"/collector/workbench?{query}" if query else "/collector/workbench"


@router.get("/collector")
def get_collector_notifications(date: str | None = None):
    current_date = _current_date(date)
    notifications = []

    for activity in db.get_all_activities():
        activity_type = str(activity.get("type") or "")
        if activity_type not in COLLECTOR_ACTIVITY_TITLES or not _on_date(
            activity, "date", current_date
        ):
            continue
        activity_id = str(activity.get("activity_id") or "")
        invoice_id = str(activity.get("invoice_id") or "")
        severity = (
            "urgent"
            if activity_type == "ptp_broken"
            else "success"
            if activity_type in {"call_completed", "ptp_honored"}
            else "warning"
            if activity_type in {"call_scheduled", "document_requested", "dispute_raised"}
            else "info"
        )
        notifications.append(
            _notification(
                notification_id=f"collector-activity:{activity_id}",
                event_type=activity_type,
                title=COLLECTOR_ACTIVITY_TITLES[activity_type],
                message=activity.get("details") or COLLECTOR_ACTIVITY_TITLES[activity_type],
                date=current_date,
                customer_id=str(activity.get("customer_id") or ""),
                invoice_id=invoice_id,
                activity_id=activity_id,
                status=str(activity.get("outcome") or ""),
                severity=severity,
                action_required=activity_type
                in {"call_scheduled", "ptp_broken", "document_requested", "dispute_raised"},
                target_url=_collector_target(activity_id, invoice_id),
            )
        )

    for communication in db.get_all_communications():
        if (
            communication.get("direction") != "inbound"
            or communication.get("type") != "email"
            or not _on_date(communication, "date", current_date)
        ):
            continue
        invoice_id = str(communication.get("invoice_id") or "")
        notifications.append(
            _notification(
                notification_id=f"collector-message:{communication.get('comm_id')}",
                event_type="customer_reply",
                title="New customer reply",
                message=communication.get("content") or "A customer sent a reply.",
                date=current_date,
                customer_id=str(communication.get("customer_id") or ""),
                invoice_id=invoice_id,
                severity="warning",
                action_required=True,
                target_url=_collector_target("", invoice_id),
            )
        )

    for payment in db.get_all_payments():
        if not _on_date(payment, "date", current_date):
            continue
        invoice_id = str(payment.get("invoice_id") or "")
        notifications.append(
            _notification(
                notification_id=f"collector-payment:{payment.get('payment_id')}",
                event_type="payment_received",
                title="Payment received",
                message=f"Payment of ${float(payment.get('amount', 0) or 0):,.2f} was recorded.",
                date=current_date,
                customer_id=str(payment.get("customer_id") or ""),
                invoice_id=invoice_id,
                severity="success",
                target_url=_collector_target("", invoice_id),
            )
        )

    return _response("collector", current_date, notifications)


def _customer_target(
    customer_id: str,
    section: str,
    invoice_id: str = "",
    dispute_id: str = "",
) -> str:
    query = urlencode(
        {
            key: value
            for key, value in {
                "section": section,
                "invoiceId": invoice_id,
                "disputeId": dispute_id,
            }.items()
            if value
        }
    )
    return f"/customer/{customer_id}/portal?{query}"


@router.get("/customer/{customer_id}")
def get_customer_notifications(
    customer_id: str, date: str | None = None
):
    if not db.get_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    current_date = _current_date(date)
    notifications = []

    for communication in db.get_communications_by_customer(customer_id):
        if (
            communication.get("direction") != "outbound"
            or communication.get("type") != "email"
            or not _on_date(communication, "date", current_date)
        ):
            continue
        invoice_id = str(communication.get("invoice_id") or "")
        notifications.append(
            _notification(
                notification_id=f"customer-message:{communication.get('comm_id')}",
                event_type="collection_message",
                title="New message from collections",
                message=communication.get("content") or "Collections sent a new message.",
                date=current_date,
                customer_id=customer_id,
                invoice_id=invoice_id,
                severity="info",
                action_required=True,
                target_url=_customer_target(customer_id, "messages", invoice_id),
            )
        )

    for payment in db.get_payments_by_customer(customer_id):
        if not _on_date(payment, "date", current_date):
            continue
        invoice_id = str(payment.get("invoice_id") or "")
        notifications.append(
            _notification(
                notification_id=f"customer-payment:{payment.get('payment_id')}",
                event_type="payment_recorded",
                title="Payment recorded",
                message=f"Your payment of ${float(payment.get('amount', 0) or 0):,.2f} was recorded.",
                date=current_date,
                customer_id=customer_id,
                invoice_id=invoice_id,
                severity="success",
                target_url=_customer_target(customer_id, "payments", invoice_id),
            )
        )

    for activity in db.get_activities_by_customer(customer_id):
        activity_type = str(activity.get("type") or "")
        if activity_type not in CUSTOMER_DISPUTE_TITLES or not _on_date(
            activity, "date", current_date
        ):
            continue
        dispute = _matching_dispute(activity)
        dispute_id = str(dispute.get("dispute_id") or "") if dispute else ""
        invoice_id = str(activity.get("invoice_id") or "")
        notifications.append(
            _notification(
                notification_id=f"customer-dispute:{activity.get('activity_id')}",
                event_type=activity_type,
                title=CUSTOMER_DISPUTE_TITLES[activity_type],
                message=activity.get("details") or CUSTOMER_DISPUTE_TITLES[activity_type],
                date=current_date,
                customer_id=customer_id,
                invoice_id=invoice_id,
                dispute_id=dispute_id,
                status=str(dispute.get("status") or "") if dispute else "",
                severity="success" if activity_type == "dispute_resolved" else "warning",
                action_required=activity_type == "dispute_information_requested",
                target_url=_customer_target(
                    customer_id, "disputes", invoice_id, dispute_id
                ),
            )
        )

    for ptp in db.get_ptps_by_customer(customer_id):
        if not _on_date(ptp, "created_date", current_date):
            continue
        invoice_id = str(ptp.get("invoice_id") or "")
        notifications.append(
            _notification(
                notification_id=f"customer-ptp:{ptp.get('ptp_id')}",
                event_type="promise_to_pay_recorded",
                title="Promise to pay recorded",
                message=f"Promise to pay ${float(ptp.get('amount', 0) or 0):,.2f} by {ptp.get('promise_date')}.",
                date=current_date,
                customer_id=customer_id,
                invoice_id=invoice_id,
                status=str(ptp.get("status") or ""),
                severity="info",
                target_url=_customer_target(customer_id, "invoices", invoice_id),
            )
        )

    return _response("customer", current_date, notifications)
