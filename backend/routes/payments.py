from fastapi import APIRouter
from pydantic import BaseModel
from backend.data_layer import excel_store as db

router = APIRouter(prefix="/api/payments", tags=["payments"])


class PaymentSubmission(BaseModel):
    customer_id: str
    invoice_id: str
    amount: float
    method: str = "Bank Transfer"


@router.get("")
def get_all_payments():
    payments = db.get_all_payments()
    return {"payments": payments}


@router.get("/customer/{customer_id}")
def get_payments_by_customer(customer_id: str):
    payments = db.get_payments_by_customer(customer_id)
    return {"payments": payments}


@router.post("")
def submit_payment(payment: PaymentSubmission):
    """Customer makes a payment via the customer portal."""
    state = db.get_system_state()
    current_date = state.get("current_date", "2026-08-01")

    payment_id = db.next_id("payments.xlsx", "payment_id", "PAY")
    pay_record = {
        "payment_id": payment_id,
        "customer_id": payment.customer_id,
        "invoice_id": payment.invoice_id,
        "amount": payment.amount,
        "date": current_date,
        "method": payment.method,
    }
    db.add_payment(pay_record)

    # Update invoice
    invoice = db.get_invoice(payment.invoice_id)
    if invoice:
        current_paid = float(invoice.get("amount_paid", 0) or 0)
        new_paid = current_paid + payment.amount
        invoice_amount = float(invoice.get("amount", 0))

        if new_paid >= invoice_amount:
            db.update_invoice(payment.invoice_id, {
                "amount_paid": new_paid,
                "paid_date": current_date,
                "status": "PAID"
            })
        else:
            db.update_invoice(payment.invoice_id, {
                "amount_paid": new_paid,
                "status": "PARTIAL_PAID"
            })

    return {"status": "recorded", "payment_id": payment_id, "amount": payment.amount}
