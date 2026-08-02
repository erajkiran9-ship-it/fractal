from fastapi import APIRouter
from backend.data_layer import excel_store as db

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def get_all_customers():
    customers = db.get_all_customers()
    return {"customers": customers}


@router.get("/{customer_id}")
def get_customer(customer_id: str):
    customer = db.get_customer(customer_id)
    if not customer:
        return {"error": "Customer not found"}, 404
    hierarchy = db.get_customer_hierarchy(customer_id)
    return {"customer": customer, "hierarchy": hierarchy}


@router.get("/{customer_id}/history")
def get_customer_history(customer_id: str):
    invoices = db.get_invoices_by_customer(customer_id)
    payments = db.get_payments_by_customer(customer_id)
    ptps = db.get_ptps_by_customer(customer_id)
    disputes = db.get_disputes_by_customer(customer_id)
    activities = db.get_activities_by_customer(customer_id)

    return {
        "customer_id": customer_id,
        "invoices": invoices,
        "payments": payments,
        "promises_to_pay": ptps,
        "disputes": disputes,
        "activities": activities,
    }
