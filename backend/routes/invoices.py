from fastapi import APIRouter
from backend.data_layer import excel_store as db
from backend.date_utils import parse_date

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("")
def get_all_invoices():
    invoices = db.get_all_invoices()
    return {"invoices": invoices}


@router.get("/open")
def get_open_invoices():
    invoices = db.get_open_invoices()
    state = db.get_system_state()
    current_date = state.get("current_date", "2026-08-01")

    results = []
    today = parse_date(current_date)
    for inv in invoices:
        due_date = parse_date(inv["due_date"])
        days_overdue = (today - due_date).days
        days_until_due = -days_overdue

        inv["days_overdue"] = max(0, days_overdue)
        inv["days_until_due"] = max(0, days_until_due)
        inv["is_overdue"] = days_overdue > 0
        results.append(inv)

    return {"invoices": results, "current_date": current_date}


@router.get("/customer/{customer_id}")
def get_invoices_by_customer(customer_id: str):
    invoices = db.get_invoices_by_customer(customer_id)
    state = db.get_system_state()
    current_date = state.get("current_date", "2026-08-01")

    today = parse_date(current_date)
    for inv in invoices:
        due_date = parse_date(inv["due_date"])
        days_overdue = (today - due_date).days
        inv["days_overdue"] = max(0, days_overdue)
        inv["is_overdue"] = days_overdue > 0

    return {"invoices": invoices, "current_date": current_date}


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str):
    invoice = db.get_invoice(invoice_id)
    if not invoice:
        return {"error": "Invoice not found"}
    return {"invoice": invoice}
