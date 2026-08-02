from fastapi import APIRouter
from pydantic import BaseModel
from backend.data_layer import excel_store as db

router = APIRouter(prefix="/api/communications", tags=["communications"])


class CustomerReply(BaseModel):
    customer_id: str
    invoice_id: str
    content: str


@router.get("")
def get_all_communications():
    comms = db.get_all_communications()
    return {"communications": comms}


@router.get("/customer/{customer_id}")
def get_communications_by_customer(customer_id: str):
    comms = db.get_communications_by_customer(customer_id)
    return {"communications": comms}


@router.get("/invoice/{invoice_id}")
def get_communications_by_invoice(invoice_id: str):
    comms = db.get_communications_by_invoice(invoice_id)
    return {"communications": comms}


@router.post("/reply")
def submit_customer_reply(reply: CustomerReply):
    """Customer replies to a collection email via the customer portal."""
    state = db.get_system_state()
    current_date = state.get("current_date", "2026-08-01")

    comm_id = db.next_id("communications.xlsx", "comm_id", "COM")
    comm = {
        "comm_id": comm_id,
        "customer_id": reply.customer_id,
        "invoice_id": reply.invoice_id,
        "direction": "inbound",
        "type": "email",
        "date": current_date,
        "content": reply.content,
        "status": "received"
    }
    db.add_communication(comm)
    return {"status": "received", "comm_id": comm_id}
