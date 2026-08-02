from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from enum import Enum


class CustomerSegment(str, Enum):
    STRATEGIC = "strategic"
    MID_TIER = "mid_tier"
    SMALL = "small"


class InvoiceStatus(str, Enum):
    OPEN = "OPEN"
    OVERDUE = "OVERDUE"
    PARTIAL_PAID = "PARTIAL_PAID"
    PAID = "PAID"
    DISPUTED = "DISPUTED"
    CLOSED = "CLOSED"


class PTPStatus(str, Enum):
    ACTIVE = "ACTIVE"
    HONORED = "HONORED"
    BROKEN = "BROKEN"


class DisputeStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    VALID = "VALID"
    INVALID = "INVALID"
    RESOLVED = "RESOLVED"


class DisputeType(str, Enum):
    PRICING_DISPUTE = "pricing_dispute"
    QUANTITY_DISPUTE = "quantity_dispute"
    QUALITY_DISPUTE = "quality_dispute"
    DELIVERY_DISPUTE = "delivery_dispute"
    TRADE_DEDUCTION = "trade_deduction"
    PROMOTIONAL_ALLOWANCE = "promotional_allowance"
    DAMAGE_CLAIM = "damage_claim"
    DUPLICATE_INVOICE = "duplicate_invoice"


class WorkflowStatus(str, Enum):
    ACTIVE = "active"
    ACTIVE_OVERDUE = "active_overdue"
    ACTIVE_PTP_MONITORING = "active_ptp_monitoring"
    ACTIVE_ESCALATED = "active_escalated"
    PAUSED_DISPUTE = "paused_dispute"
    PAUSED_DOCUMENT = "paused_document"
    CLOSED = "closed"


class CreditStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    HOLD = "HOLD"


class ActivityType(str, Enum):
    EMAIL_SENT = "email_sent"
    CALL_SCHEDULED = "call_scheduled"
    CALL_COMPLETED = "call_completed"
    ESCALATION = "escalation"
    PTP_LOGGED = "ptp_logged"
    PTP_BROKEN = "ptp_broken"
    PTP_HONORED = "ptp_honored"
    DISPUTE_RAISED = "dispute_raised"
    DISPUTE_ROUTED = "dispute_routed"
    DOCUMENT_REQUESTED = "document_requested"
    DOCUMENT_RECEIVED = "document_received"
    PAYMENT_RECEIVED = "payment_received"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_MODIFIED = "workflow_modified"
    WORKFLOW_CLOSED = "workflow_closed"
    CREDIT_ALERT = "credit_alert"
    CREDIT_HOLD = "credit_hold"


class CommunicationDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CommunicationType(str, Enum):
    EMAIL = "email"
    CALL_NOTES = "call_notes"
    CALL_SCRIPT = "call_script"
    SYSTEM_NOTE = "system_note"


class Customer(BaseModel):
    customer_id: str
    name: str
    parent_customer_id: Optional[str] = None
    segment: CustomerSegment
    strategic: bool = False
    credit_limit: float
    annual_revenue: float
    payment_terms: str = "Net 30"
    contact_name: str
    contact_email: str
    avg_days_to_pay: int = 0


class Invoice(BaseModel):
    invoice_id: str
    customer_id: str
    amount: float
    issue_date: date
    due_date: date
    status: InvoiceStatus = InvoiceStatus.OPEN
    amount_paid: float = 0.0
    paid_date: Optional[date] = None


class Payment(BaseModel):
    payment_id: str
    customer_id: str
    invoice_id: str
    amount: float
    date: date
    method: str = "Bank Transfer"


class PromiseToPay(BaseModel):
    ptp_id: str
    customer_id: str
    invoice_id: str
    amount: float
    promise_date: date
    status: PTPStatus = PTPStatus.ACTIVE
    created_date: date
    source: str = "email"


class Dispute(BaseModel):
    dispute_id: str
    customer_id: str
    invoice_id: str
    type: DisputeType
    amount: float
    reason: str
    status: DisputeStatus = DisputeStatus.OPEN
    owner: Optional[str] = None
    created_date: date
    assigned_date: Optional[date] = None
    investigation_notes: str = ""
    decision: Optional[str] = None
    approved_amount: float = 0.0
    team_response: str = ""
    resolved_by: Optional[str] = None
    resolved_date: Optional[date] = None
    remaining_balance: Optional[float] = None
    updated_date: Optional[date] = None


class Activity(BaseModel):
    activity_id: str
    customer_id: str
    invoice_id: str
    type: ActivityType
    date: date
    details: str
    outcome: Optional[str] = None


class Communication(BaseModel):
    comm_id: str
    customer_id: str
    invoice_id: str
    direction: CommunicationDirection
    type: CommunicationType
    date: date
    content: str
    status: str = "sent"


class Document(BaseModel):
    doc_id: str
    customer_id: str
    invoice_id: str
    doc_type: str
    file_path: str
    uploaded_date: date


class WorkflowState(BaseModel):
    workflow_id: str
    invoice_id: str
    customer_id: str
    status: WorkflowStatus
    plan_json: str
    reasoning: str
    confidence: int
    reason_code: str
    last_updated: datetime


class CreditExposure(BaseModel):
    customer_id: str
    credit_limit: float
    current_exposure: float
    available_credit: float
    percentage_used: float
    status: CreditStatus


class SystemState(BaseModel):
    current_date: date
    last_cycle_date: Optional[date] = None
    cycle_count: int = 0
