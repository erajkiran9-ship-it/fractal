import pandas as pd
import os
import json
from datetime import date, datetime
from typing import Optional
from pathlib import Path
from backend.date_utils import parse_datetime

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "incoming_invoices").mkdir(exist_ok=True)
    (DATA_DIR / "documents").mkdir(exist_ok=True)
    (DATA_DIR / "emails").mkdir(exist_ok=True)


def _read_excel(filename: str) -> pd.DataFrame:
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return pd.DataFrame()
    df = pd.read_excel(filepath)
    df = df.fillna("")
    return df


def _write_excel(filename: str, df: pd.DataFrame):
    _ensure_data_dir()
    filepath = DATA_DIR / filename
    df.to_excel(filepath, index=False)


def _append_row(filename: str, row: dict) -> dict:
    df = _read_excel(filename)
    new_df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _write_excel(filename, new_df)
    return row


def _update_row(filename: str, id_column: str, id_value: str, updates: dict):
    df = _read_excel(filename)
    mask = df[id_column] == id_value
    if mask.any():
        for key, value in updates.items():
            df.loc[mask, key] = value
        _write_excel(filename, df)
        return True
    return False


# ─── SYSTEM STATE ───

def get_system_state() -> dict:
    filepath = DATA_DIR / "system_state.json"
    if not filepath.exists():
        return {"current_date": "2026-08-01", "last_cycle_date": None, "cycle_count": 0}
    with open(filepath, "r") as f:
        return json.load(f)


def save_system_state(state: dict):
    _ensure_data_dir()
    filepath = DATA_DIR / "system_state.json"
    with open(filepath, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ─── CUSTOMERS ───

def get_all_customers() -> list[dict]:
    df = _read_excel("customers.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_customer(customer_id: str) -> Optional[dict]:
    df = _read_excel("customers.xlsx")
    if df.empty:
        return None
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        return None
    return row.to_dict("records")[0]


def get_customer_by_name(name: str) -> Optional[dict]:
    df = _read_excel("customers.xlsx")
    if df.empty:
        return None
    row = df[df["name"].str.lower().str.contains(name.lower())]
    if row.empty:
        return None
    return row.to_dict("records")[0]


def get_customer_hierarchy(customer_id: str) -> dict:
    df = _read_excel("customers.xlsx")
    if df.empty:
        return {"parent": None, "children": []}
    customer = df[df["customer_id"] == customer_id]
    if customer.empty:
        return {"parent": None, "children": []}

    customer_rec = customer.to_dict("records")[0]
    parent_id = customer_rec.get("parent_customer_id")

    parent = None
    if parent_id and pd.notna(parent_id):
        parent_row = df[df["customer_id"] == parent_id]
        if not parent_row.empty:
            parent = parent_row.to_dict("records")[0]

    children = df[df["parent_customer_id"] == customer_id].to_dict("records")

    return {"parent": parent, "children": children}


# ─── INVOICES ───

def get_all_invoices() -> list[dict]:
    df = _read_excel("invoices.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_open_invoices() -> list[dict]:
    df = _read_excel("invoices.xlsx")
    if df.empty:
        return []
    open_statuses = ["OPEN", "OVERDUE", "PARTIAL_PAID", "DISPUTED"]
    filtered = df[df["status"].isin(open_statuses)]
    return filtered.to_dict("records")


def get_invoices_by_customer(customer_id: str) -> list[dict]:
    df = _read_excel("invoices.xlsx")
    if df.empty:
        return []
    filtered = df[df["customer_id"] == customer_id]
    return filtered.to_dict("records")


def get_invoice(invoice_id: str) -> Optional[dict]:
    df = _read_excel("invoices.xlsx")
    if df.empty:
        return None
    row = df[df["invoice_id"] == invoice_id]
    if row.empty:
        return None
    return row.to_dict("records")[0]


def add_invoice(invoice: dict) -> dict:
    return _append_row("invoices.xlsx", invoice)


def update_invoice(invoice_id: str, updates: dict) -> bool:
    return _update_row("invoices.xlsx", "invoice_id", invoice_id, updates)


# ─── PAYMENTS ───

def get_all_payments() -> list[dict]:
    df = _read_excel("payments.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_payments_by_customer(customer_id: str) -> list[dict]:
    df = _read_excel("payments.xlsx")
    if df.empty:
        return []
    return df[df["customer_id"] == customer_id].to_dict("records")


def get_payments_by_invoice(invoice_id: str) -> list[dict]:
    df = _read_excel("payments.xlsx")
    if df.empty:
        return []
    return df[df["invoice_id"] == invoice_id].to_dict("records")


def add_payment(payment: dict) -> dict:
    return _append_row("payments.xlsx", payment)


def _get_records_since(
    filename: str,
    since_date: str,
    *,
    direction: Optional[str] = None,
) -> list[dict]:
    """Filter dated Excel records without pandas datetime conversion."""
    df = _read_excel(filename)
    if df.empty:
        return []

    threshold = parse_datetime(since_date)
    filtered = []
    for record in df.to_dict("records"):
        if direction is not None and record.get("direction") != direction:
            continue
        try:
            record_date = parse_datetime(record.get("date"))
        except (TypeError, ValueError):
            continue
        if record_date >= threshold:
            record["date"] = record_date
            filtered.append(record)
    return filtered


def get_new_payments_since(since_date: str) -> list[dict]:
    return _get_records_since("payments.xlsx", since_date)


# ─── PROMISES TO PAY ───

def get_all_ptps() -> list[dict]:
    df = _read_excel("promises_to_pay.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_ptps_by_customer(customer_id: str) -> list[dict]:
    df = _read_excel("promises_to_pay.xlsx")
    if df.empty:
        return []
    return df[df["customer_id"] == customer_id].to_dict("records")


def get_active_ptps() -> list[dict]:
    df = _read_excel("promises_to_pay.xlsx")
    if df.empty:
        return []
    return df[df["status"] == "ACTIVE"].to_dict("records")


def add_ptp(ptp: dict) -> dict:
    return _append_row("promises_to_pay.xlsx", ptp)


def update_ptp(ptp_id: str, updates: dict) -> bool:
    return _update_row("promises_to_pay.xlsx", "ptp_id", ptp_id, updates)


# ─── DISPUTES ───

def get_all_disputes() -> list[dict]:
    df = _read_excel("disputes.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_dispute(dispute_id: str) -> Optional[dict]:
    df = _read_excel("disputes.xlsx")
    if df.empty:
        return None
    row = df[df["dispute_id"] == dispute_id]
    if row.empty:
        return None
    return row.to_dict("records")[0]


def get_disputes_by_customer(customer_id: str) -> list[dict]:
    df = _read_excel("disputes.xlsx")
    if df.empty:
        return []
    return df[df["customer_id"] == customer_id].to_dict("records")


def get_open_disputes() -> list[dict]:
    df = _read_excel("disputes.xlsx")
    if df.empty:
        return []
    open_statuses = ["OPEN", "UNDER_REVIEW", "NEEDS_INFORMATION"]
    return df[df["status"].isin(open_statuses)].to_dict("records")


def add_dispute(dispute: dict) -> dict:
    return _append_row("disputes.xlsx", dispute)


def update_dispute(dispute_id: str, updates: dict) -> bool:
    return _update_row("disputes.xlsx", "dispute_id", dispute_id, updates)


# ─── ACTIVITIES ───

def get_all_activities() -> list[dict]:
    df = _read_excel("activities.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_activities_by_invoice(invoice_id: str) -> list[dict]:
    df = _read_excel("activities.xlsx")
    if df.empty:
        return []
    return df[df["invoice_id"] == invoice_id].to_dict("records")


def get_activities_by_customer(customer_id: str) -> list[dict]:
    df = _read_excel("activities.xlsx")
    if df.empty:
        return []
    return df[df["customer_id"] == customer_id].to_dict("records")


def add_activity(activity: dict) -> dict:
    return _append_row("activities.xlsx", activity)


def get_new_activities_since(since_date: str) -> list[dict]:
    return _get_records_since("activities.xlsx", since_date)


# ─── COMMUNICATIONS ───

def get_all_communications() -> list[dict]:
    df = _read_excel("communications.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_communications_by_customer(customer_id: str) -> list[dict]:
    df = _read_excel("communications.xlsx")
    if df.empty:
        return []
    return df[df["customer_id"] == customer_id].to_dict("records")


def get_communications_by_invoice(invoice_id: str) -> list[dict]:
    df = _read_excel("communications.xlsx")
    if df.empty:
        return []
    return df[df["invoice_id"] == invoice_id].to_dict("records")


def get_new_inbound_since(since_date: str) -> list[dict]:
    return _get_records_since(
        "communications.xlsx",
        since_date,
        direction="inbound",
    )


def add_communication(comm: dict) -> dict:
    return _append_row("communications.xlsx", comm)


# ─── DOCUMENTS ───

def get_all_documents() -> list[dict]:
    df = _read_excel("documents.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_documents_by_invoice(invoice_id: str) -> list[dict]:
    df = _read_excel("documents.xlsx")
    if df.empty:
        return []
    return df[df["invoice_id"] == invoice_id].to_dict("records")


def get_documents_by_customer(customer_id: str) -> list[dict]:
    df = _read_excel("documents.xlsx")
    if df.empty:
        return []
    return df[df["customer_id"] == customer_id].to_dict("records")


def add_document(doc: dict) -> dict:
    return _append_row("documents.xlsx", doc)


# ─── WORKFLOW STATES ───

def get_all_workflows() -> list[dict]:
    df = _read_excel("workflow_states.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_active_workflows() -> list[dict]:
    df = _read_excel("workflow_states.xlsx")
    if df.empty:
        return []
    closed = ["closed"]
    return df[~df["status"].isin(closed)].to_dict("records")


def get_workflow_by_invoice(invoice_id: str) -> Optional[dict]:
    df = _read_excel("workflow_states.xlsx")
    if df.empty:
        return None
    row = df[df["invoice_id"] == invoice_id]
    if row.empty:
        return None
    return row.to_dict("records")[0]


def add_workflow(workflow: dict) -> dict:
    return _append_row("workflow_states.xlsx", workflow)


def update_workflow(invoice_id: str, updates: dict) -> bool:
    df = _read_excel("workflow_states.xlsx")
    if df.empty:
        return False
    mask = df["invoice_id"] == invoice_id
    if mask.any():
        for key, value in updates.items():
            df.loc[mask, key] = value
        _write_excel("workflow_states.xlsx", df)
        return True
    return False


# ─── CREDIT EXPOSURE ───

def get_all_credit_exposure() -> list[dict]:
    df = _read_excel("credit_exposure.xlsx")
    if df.empty:
        return []
    return df.to_dict("records")


def get_credit_exposure(customer_id: str) -> Optional[dict]:
    df = _read_excel("credit_exposure.xlsx")
    if df.empty:
        return None
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        return None
    return row.to_dict("records")[0]


def update_credit_exposure(customer_id: str, updates: dict) -> bool:
    return _update_row("credit_exposure.xlsx", "customer_id", customer_id, updates)


# ─── INCOMING INVOICES FOLDER ───

def scan_incoming_invoices() -> list[str]:
    incoming_dir = DATA_DIR / "incoming_invoices"
    if not incoming_dir.exists():
        return []
    return [f for f in os.listdir(incoming_dir) if f.lower().endswith(".pdf")]


def move_processed_invoice(filename: str):
    src = DATA_DIR / "incoming_invoices" / filename
    dst = DATA_DIR / "documents" / filename
    if src.exists():
        src.rename(dst)


# ─── HELPER: NEXT ID GENERATORS ───

def next_id(filename: str, id_column: str, prefix: str) -> str:
    df = _read_excel(filename)
    if df.empty:
        return f"{prefix}-001"
    existing = df[id_column].tolist()
    nums = []
    for eid in existing:
        try:
            num = int(str(eid).split("-")[-1])
            nums.append(num)
        except (ValueError, IndexError):
            pass
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}-{next_num:03d}"
