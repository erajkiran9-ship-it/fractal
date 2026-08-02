"""
Generates all synthetic historical data for the CPG Collections Workflow Agent.
Creates Excel files with 5 months of history (March-July 2026) for 3 customers.
System starts at Aug 1, 2026 with no active invoices.
"""

import pandas as pd
import json
import os
import sys
from pathlib import Path
from datetime import date

DATA_DIR = Path(__file__).parent.parent / "data"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "incoming_invoices").mkdir(exist_ok=True)
    (DATA_DIR / "documents").mkdir(exist_ok=True)
    (DATA_DIR / "emails").mkdir(exist_ok=True)


def generate_customers():
    customers = [
        {
            "customer_id": "CUST-001",
            "name": "FreshMart Grocers",
            "parent_customer_id": None,
            "segment": "mid_tier",
            "strategic": False,
            "credit_limit": 200000,
            "annual_revenue": 450000,
            "payment_terms": "Net 30",
            "contact_name": "Mary Johnson",
            "contact_email": "mary@freshmart.com",
            "avg_days_to_pay": 14,
        },
        {
            "customer_id": "CUST-001A",
            "name": "FreshMart Downtown",
            "parent_customer_id": "CUST-001",
            "segment": "mid_tier",
            "strategic": False,
            "credit_limit": 200000,
            "annual_revenue": 180000,
            "payment_terms": "Net 30",
            "contact_name": "Mary Johnson",
            "contact_email": "mary@freshmart.com",
            "avg_days_to_pay": 14,
        },
        {
            "customer_id": "CUST-001B",
            "name": "FreshMart Westside",
            "parent_customer_id": "CUST-001",
            "segment": "mid_tier",
            "strategic": False,
            "credit_limit": 200000,
            "annual_revenue": 150000,
            "payment_terms": "Net 30",
            "contact_name": "Mary Johnson",
            "contact_email": "mary@freshmart.com",
            "avg_days_to_pay": 14,
        },
        {
            "customer_id": "CUST-001C",
            "name": "FreshMart Airport",
            "parent_customer_id": "CUST-001",
            "segment": "mid_tier",
            "strategic": False,
            "credit_limit": 200000,
            "annual_revenue": 120000,
            "payment_terms": "Net 30",
            "contact_name": "Mary Johnson",
            "contact_email": "mary@freshmart.com",
            "avg_days_to_pay": 14,
        },
        {
            "customer_id": "CUST-002",
            "name": "MegaMart Holdings",
            "parent_customer_id": None,
            "segment": "strategic",
            "strategic": True,
            "credit_limit": 1000000,
            "annual_revenue": 12000000,
            "payment_terms": "Net 45",
            "contact_name": "Robert Chen",
            "contact_email": "robert.chen@megamart.com",
            "avg_days_to_pay": 8,
        },
        {
            "customer_id": "CUST-002A",
            "name": "MegaMart Region East",
            "parent_customer_id": "CUST-002",
            "segment": "strategic",
            "strategic": True,
            "credit_limit": 1000000,
            "annual_revenue": 6000000,
            "payment_terms": "Net 45",
            "contact_name": "Robert Chen",
            "contact_email": "robert.chen@megamart.com",
            "avg_days_to_pay": 8,
        },
        {
            "customer_id": "CUST-002B",
            "name": "MegaMart Region West",
            "parent_customer_id": "CUST-002",
            "segment": "strategic",
            "strategic": True,
            "credit_limit": 1000000,
            "annual_revenue": 6000000,
            "payment_terms": "Net 45",
            "contact_name": "Lisa Park",
            "contact_email": "lisa.park@megamart.com",
            "avg_days_to_pay": 8,
        },
        {
            "customer_id": "CUST-003",
            "name": "QuickStop Convenience",
            "parent_customer_id": None,
            "segment": "small",
            "strategic": False,
            "credit_limit": 70000,
            "annual_revenue": 180000,
            "payment_terms": "Net 30",
            "contact_name": "David Miller",
            "contact_email": "david@quickstop.com",
            "avg_days_to_pay": 20,
        },
        {
            "customer_id": "CUST-003A",
            "name": "QuickStop North",
            "parent_customer_id": "CUST-003",
            "segment": "small",
            "strategic": False,
            "credit_limit": 70000,
            "annual_revenue": 100000,
            "payment_terms": "Net 30",
            "contact_name": "David Miller",
            "contact_email": "david@quickstop.com",
            "avg_days_to_pay": 20,
        },
        {
            "customer_id": "CUST-003B",
            "name": "QuickStop South",
            "parent_customer_id": "CUST-003",
            "segment": "small",
            "strategic": False,
            "credit_limit": 70000,
            "annual_revenue": 80000,
            "payment_terms": "Net 30",
            "contact_name": "David Miller",
            "contact_email": "david@quickstop.com",
            "avg_days_to_pay": 20,
        },
    ]
    return pd.DataFrame(customers)


def generate_invoices():
    invoices = [
        # FreshMart - 5 months (all paid/closed)
        {"invoice_id": "INV-1001", "customer_id": "CUST-001", "amount": 32000, "issue_date": "2026-03-01", "due_date": "2026-03-31", "status": "CLOSED", "amount_paid": 32000, "paid_date": "2026-04-05"},
        {"invoice_id": "INV-1002", "customer_id": "CUST-001", "amount": 41500, "issue_date": "2026-04-01", "due_date": "2026-05-01", "status": "CLOSED", "amount_paid": 41500, "paid_date": "2026-05-12"},
        {"invoice_id": "INV-1003", "customer_id": "CUST-001", "amount": 38700, "issue_date": "2026-05-01", "due_date": "2026-05-31", "status": "CLOSED", "amount_paid": 38700, "paid_date": "2026-06-05"},
        {"invoice_id": "INV-1004", "customer_id": "CUST-001", "amount": 47200, "issue_date": "2026-06-01", "due_date": "2026-06-30", "status": "CLOSED", "amount_paid": 47200, "paid_date": "2026-07-22"},
        {"invoice_id": "INV-1005", "customer_id": "CUST-001", "amount": 44100, "issue_date": "2026-07-01", "due_date": "2026-07-25", "status": "CLOSED", "amount_paid": 44100, "paid_date": "2026-08-01"},
        # MegaMart - 5 months (all paid/closed)
        {"invoice_id": "INV-2001", "customer_id": "CUST-002", "amount": 125000, "issue_date": "2026-03-01", "due_date": "2026-04-15", "status": "CLOSED", "amount_paid": 125000, "paid_date": "2026-04-14"},
        {"invoice_id": "INV-2002", "customer_id": "CUST-002", "amount": 132400, "issue_date": "2026-04-01", "due_date": "2026-05-15", "status": "CLOSED", "amount_paid": 132400, "paid_date": "2026-05-20"},
        {"invoice_id": "INV-2003", "customer_id": "CUST-002", "amount": 118900, "issue_date": "2026-05-01", "due_date": "2026-06-15", "status": "CLOSED", "amount_paid": 118900, "paid_date": "2026-06-25"},
        {"invoice_id": "INV-2004", "customer_id": "CUST-002", "amount": 141200, "issue_date": "2026-06-01", "due_date": "2026-07-15", "status": "CLOSED", "amount_paid": 141200, "paid_date": "2026-07-28"},
        {"invoice_id": "INV-2005", "customer_id": "CUST-002", "amount": 128500, "issue_date": "2026-07-01", "due_date": "2026-08-15", "status": "CLOSED", "amount_paid": 128500, "paid_date": "2026-07-30"},
        # QuickStop - 5 months (all paid/closed, seasonal pattern visible)
        {"invoice_id": "INV-3001", "customer_id": "CUST-003", "amount": 18200, "issue_date": "2026-03-01", "due_date": "2026-03-31", "status": "CLOSED", "amount_paid": 18200, "paid_date": "2026-04-08"},
        {"invoice_id": "INV-3002", "customer_id": "CUST-003", "amount": 22100, "issue_date": "2026-04-01", "due_date": "2026-05-01", "status": "CLOSED", "amount_paid": 22100, "paid_date": "2026-05-16"},
        {"invoice_id": "INV-3003", "customer_id": "CUST-003", "amount": 19800, "issue_date": "2026-05-01", "due_date": "2026-05-31", "status": "CLOSED", "amount_paid": 19800, "paid_date": "2026-06-25"},
        {"invoice_id": "INV-3004", "customer_id": "CUST-003", "amount": 24500, "issue_date": "2026-06-01", "due_date": "2026-06-30", "status": "CLOSED", "amount_paid": 24500, "paid_date": "2026-08-01"},
        {"invoice_id": "INV-3005", "customer_id": "CUST-003", "amount": 21300, "issue_date": "2026-07-01", "due_date": "2026-07-31", "status": "CLOSED", "amount_paid": 21300, "paid_date": "2026-08-01"},
    ]
    return pd.DataFrame(invoices)


def generate_payments():
    payments = [
        {"payment_id": "PAY-001", "customer_id": "CUST-001", "invoice_id": "INV-1001", "amount": 32000, "date": "2026-04-05", "method": "Bank Transfer"},
        {"payment_id": "PAY-002", "customer_id": "CUST-001", "invoice_id": "INV-1002", "amount": 41500, "date": "2026-05-12", "method": "Bank Transfer"},
        {"payment_id": "PAY-003", "customer_id": "CUST-001", "invoice_id": "INV-1003", "amount": 38700, "date": "2026-06-05", "method": "Bank Transfer"},
        {"payment_id": "PAY-004", "customer_id": "CUST-001", "invoice_id": "INV-1004", "amount": 47200, "date": "2026-07-22", "method": "Bank Transfer"},
        {"payment_id": "PAY-005", "customer_id": "CUST-001", "invoice_id": "INV-1005", "amount": 44100, "date": "2026-08-01", "method": "Bank Transfer"},
        {"payment_id": "PAY-006", "customer_id": "CUST-002", "invoice_id": "INV-2001", "amount": 125000, "date": "2026-04-14", "method": "Wire Transfer"},
        {"payment_id": "PAY-007", "customer_id": "CUST-002", "invoice_id": "INV-2002", "amount": 102400, "date": "2026-05-18", "method": "Wire Transfer"},
        {"payment_id": "PAY-008", "customer_id": "CUST-002", "invoice_id": "INV-2002", "amount": 30000, "date": "2026-06-01", "method": "Wire Transfer"},
        {"payment_id": "PAY-009", "customer_id": "CUST-002", "invoice_id": "INV-2003", "amount": 118900, "date": "2026-06-25", "method": "Wire Transfer"},
        {"payment_id": "PAY-010", "customer_id": "CUST-002", "invoice_id": "INV-2004", "amount": 111200, "date": "2026-07-18", "method": "Wire Transfer"},
        {"payment_id": "PAY-011", "customer_id": "CUST-002", "invoice_id": "INV-2004", "amount": 30000, "date": "2026-07-28", "method": "Wire Transfer"},
        {"payment_id": "PAY-012", "customer_id": "CUST-002", "invoice_id": "INV-2005", "amount": 128500, "date": "2026-07-30", "method": "Wire Transfer"},
        {"payment_id": "PAY-013", "customer_id": "CUST-003", "invoice_id": "INV-3001", "amount": 18200, "date": "2026-04-08", "method": "Check"},
        {"payment_id": "PAY-014", "customer_id": "CUST-003", "invoice_id": "INV-3002", "amount": 22100, "date": "2026-05-16", "method": "Check"},
        {"payment_id": "PAY-015", "customer_id": "CUST-003", "invoice_id": "INV-3003", "amount": 19800, "date": "2026-06-25", "method": "Check"},
        {"payment_id": "PAY-016", "customer_id": "CUST-003", "invoice_id": "INV-3004", "amount": 24500, "date": "2026-08-01", "method": "Bank Transfer"},
        {"payment_id": "PAY-017", "customer_id": "CUST-003", "invoice_id": "INV-3005", "amount": 21300, "date": "2026-08-01", "method": "Bank Transfer"},
    ]
    return pd.DataFrame(payments)


def generate_promises_to_pay():
    ptps = [
        {"ptp_id": "PTP-001", "customer_id": "CUST-001", "invoice_id": "INV-1003", "amount": 38700, "promise_date": "2026-06-05", "status": "HONORED", "created_date": "2026-06-02", "source": "email"},
        {"ptp_id": "PTP-002", "customer_id": "CUST-001", "invoice_id": "INV-1004", "amount": 47200, "promise_date": "2026-07-10", "status": "BROKEN", "created_date": "2026-07-05", "source": "call"},
    ]
    return pd.DataFrame(ptps)


def generate_disputes():
    disputes = [
        {"dispute_id": "DSP-001", "customer_id": "CUST-002", "invoice_id": "INV-2002", "type": "promotional_allowance", "amount": 30000, "reason": "Q1 Promo Allowance - PO #3301", "status": "RESOLVED", "owner": "trade_team", "created_date": "2026-05-18", "resolved_date": "2026-05-28"},
        {"dispute_id": "DSP-002", "customer_id": "CUST-002", "invoice_id": "INV-2004", "type": "trade_deduction", "amount": 30000, "reason": "Q2 Promo Discount - PO #4412", "status": "RESOLVED", "owner": "trade_team", "created_date": "2026-07-18", "resolved_date": "2026-07-25"},
    ]
    return pd.DataFrame(disputes)


def generate_activities():
    activities = [
        # FreshMart INV-1001: paid after reminder
        {"activity_id": "ACT-001", "customer_id": "CUST-001", "invoice_id": "INV-1001", "type": "email_sent", "date": "2026-04-03", "details": "Friendly reminder sent for INV-1001", "outcome": "payment_received"},
        # FreshMart INV-1002: paid after call
        {"activity_id": "ACT-002", "customer_id": "CUST-001", "invoice_id": "INV-1002", "type": "email_sent", "date": "2026-05-04", "details": "Friendly reminder sent for INV-1002", "outcome": "no_response"},
        {"activity_id": "ACT-003", "customer_id": "CUST-001", "invoice_id": "INV-1002", "type": "call_completed", "date": "2026-05-08", "details": "Called Mary. She said payment is processing.", "outcome": "payment_confirmed"},
        # FreshMart INV-1003: PTP honored
        {"activity_id": "ACT-004", "customer_id": "CUST-001", "invoice_id": "INV-1003", "type": "email_sent", "date": "2026-06-02", "details": "Reminder sent for INV-1003", "outcome": "ptp_received"},
        {"activity_id": "ACT-005", "customer_id": "CUST-001", "invoice_id": "INV-1003", "type": "ptp_logged", "date": "2026-06-02", "details": "PTP: $38,700 by Jun 5. Source: email reply", "outcome": "honored"},
        # FreshMart INV-1004: PTP broken, escalated
        {"activity_id": "ACT-006", "customer_id": "CUST-001", "invoice_id": "INV-1004", "type": "email_sent", "date": "2026-07-03", "details": "Reminder sent for INV-1004", "outcome": "no_response"},
        {"activity_id": "ACT-007", "customer_id": "CUST-001", "invoice_id": "INV-1004", "type": "call_completed", "date": "2026-07-05", "details": "Called Mary. PTP received: $47,200 by Jul 10", "outcome": "ptp_received"},
        {"activity_id": "ACT-008", "customer_id": "CUST-001", "invoice_id": "INV-1004", "type": "ptp_logged", "date": "2026-07-05", "details": "PTP: $47,200 by Jul 10. Source: call", "outcome": "broken"},
        {"activity_id": "ACT-009", "customer_id": "CUST-001", "invoice_id": "INV-1004", "type": "ptp_broken", "date": "2026-07-11", "details": "PTP deadline passed. No payment received.", "outcome": "escalated"},
        {"activity_id": "ACT-010", "customer_id": "CUST-001", "invoice_id": "INV-1004", "type": "escalation", "date": "2026-07-11", "details": "Escalated to collections manager. Broken PTP.", "outcome": "manager_called"},
        {"activity_id": "ACT-011", "customer_id": "CUST-001", "invoice_id": "INV-1004", "type": "call_completed", "date": "2026-07-14", "details": "Manager called Mary. She committed to paying by Jul 22.", "outcome": "payment_received"},
        # FreshMart INV-1005: paid after reminder
        {"activity_id": "ACT-012", "customer_id": "CUST-001", "invoice_id": "INV-1005", "type": "email_sent", "date": "2026-07-28", "details": "Reminder sent for INV-1005", "outcome": "payment_received"},
        # MegaMart INV-2002: partial pay + valid deduction
        {"activity_id": "ACT-013", "customer_id": "CUST-002", "invoice_id": "INV-2002", "type": "email_sent", "date": "2026-05-20", "details": "Gentle reminder for remaining balance", "outcome": "deduction_identified"},
        {"activity_id": "ACT-014", "customer_id": "CUST-002", "invoice_id": "INV-2002", "type": "dispute_routed", "date": "2026-05-20", "details": "Trade deduction $30K routed to trade team", "outcome": "valid_deduction"},
        # MegaMart INV-2003: paid after gentle reminder
        {"activity_id": "ACT-015", "customer_id": "CUST-002", "invoice_id": "INV-2003", "type": "email_sent", "date": "2026-06-20", "details": "Gentle reminder for INV-2003", "outcome": "payment_received"},
        # MegaMart INV-2004: partial pay + invalid deduction recovered
        {"activity_id": "ACT-016", "customer_id": "CUST-002", "invoice_id": "INV-2004", "type": "email_sent", "date": "2026-07-20", "details": "Noticed partial payment, investigating shortfall", "outcome": "deduction_identified"},
        {"activity_id": "ACT-017", "customer_id": "CUST-002", "invoice_id": "INV-2004", "type": "dispute_routed", "date": "2026-07-20", "details": "Trade deduction $30K routed to trade team for validation", "outcome": "invalid_deduction"},
        {"activity_id": "ACT-018", "customer_id": "CUST-002", "invoice_id": "INV-2004", "type": "email_sent", "date": "2026-07-25", "details": "Informed MegaMart deduction invalid. Promo agreement attached showing SKU mismatch.", "outcome": "payment_received"},
        # QuickStop: seasonal late payments
        {"activity_id": "ACT-019", "customer_id": "CUST-003", "invoice_id": "INV-3001", "type": "email_sent", "date": "2026-04-03", "details": "Reminder for INV-3001", "outcome": "payment_received"},
        {"activity_id": "ACT-020", "customer_id": "CUST-003", "invoice_id": "INV-3002", "type": "email_sent", "date": "2026-05-04", "details": "Reminder for INV-3002", "outcome": "no_response"},
        {"activity_id": "ACT-021", "customer_id": "CUST-003", "invoice_id": "INV-3002", "type": "call_completed", "date": "2026-05-10", "details": "Called David. Summer slowdown affecting cash.", "outcome": "payment_received"},
        {"activity_id": "ACT-022", "customer_id": "CUST-003", "invoice_id": "INV-3003", "type": "email_sent", "date": "2026-06-03", "details": "Reminder for INV-3003", "outcome": "no_response"},
        {"activity_id": "ACT-023", "customer_id": "CUST-003", "invoice_id": "INV-3003", "type": "email_sent", "date": "2026-06-10", "details": "Follow-up for INV-3003", "outcome": "no_response"},
        {"activity_id": "ACT-024", "customer_id": "CUST-003", "invoice_id": "INV-3003", "type": "call_completed", "date": "2026-06-15", "details": "David confirmed summer cash issues. Seasonal pattern.", "outcome": "payment_received"},
        {"activity_id": "ACT-025", "customer_id": "CUST-003", "invoice_id": "INV-3004", "type": "email_sent", "date": "2026-07-03", "details": "Reminder for INV-3004", "outcome": "no_response"},
        {"activity_id": "ACT-026", "customer_id": "CUST-003", "invoice_id": "INV-3004", "type": "email_sent", "date": "2026-07-10", "details": "Follow-up for INV-3004", "outcome": "no_response"},
        {"activity_id": "ACT-027", "customer_id": "CUST-003", "invoice_id": "INV-3004", "type": "call_completed", "date": "2026-07-15", "details": "Called David. Typical summer delay. Expected payment by end of July.", "outcome": "payment_received"},
        {"activity_id": "ACT-028", "customer_id": "CUST-003", "invoice_id": "INV-3005", "type": "email_sent", "date": "2026-08-01", "details": "Reminder for INV-3005. Noted seasonal pattern.", "outcome": "payment_received"},
    ]
    return pd.DataFrame(activities)


def generate_communications():
    comms = [
        {"comm_id": "COM-001", "customer_id": "CUST-001", "invoice_id": "INV-1001", "direction": "outbound", "type": "email", "date": "2026-04-03", "content": "Hi Mary, friendly reminder that invoice INV-1001 for $32,000 is now past due. Please arrange payment at your convenience.", "status": "sent"},
        {"comm_id": "COM-002", "customer_id": "CUST-001", "invoice_id": "INV-1002", "direction": "outbound", "type": "email", "date": "2026-05-04", "content": "Hi Mary, this is a reminder regarding invoice INV-1002 for $41,500 which was due on May 1.", "status": "sent"},
        {"comm_id": "COM-003", "customer_id": "CUST-001", "invoice_id": "INV-1002", "direction": "inbound", "type": "call_notes", "date": "2026-05-08", "content": "Spoke with Mary. She said payment is processing, expect by May 12.", "status": "received"},
        {"comm_id": "COM-004", "customer_id": "CUST-001", "invoice_id": "INV-1003", "direction": "outbound", "type": "email", "date": "2026-06-02", "content": "Hi Mary, invoice INV-1003 for $38,700 is now due. Please let us know your payment timeline.", "status": "sent"},
        {"comm_id": "COM-005", "customer_id": "CUST-001", "invoice_id": "INV-1003", "direction": "inbound", "type": "email", "date": "2026-06-02", "content": "I'll pay by June 5.", "status": "received"},
        {"comm_id": "COM-006", "customer_id": "CUST-001", "invoice_id": "INV-1004", "direction": "outbound", "type": "email", "date": "2026-07-03", "content": "Hi Mary, invoice INV-1004 for $47,200 was due June 30 and remains unpaid. Please arrange payment.", "status": "sent"},
        {"comm_id": "COM-007", "customer_id": "CUST-001", "invoice_id": "INV-1004", "direction": "inbound", "type": "call_notes", "date": "2026-07-05", "content": "Mary committed to paying by Jul 10. Cash flow tight this month.", "status": "received"},
        {"comm_id": "COM-008", "customer_id": "CUST-001", "invoice_id": "INV-1004", "direction": "outbound", "type": "email", "date": "2026-07-11", "content": "Payment was expected by Jul 10 and has not arrived. This is being escalated to management.", "status": "sent"},
        {"comm_id": "COM-009", "customer_id": "CUST-001", "invoice_id": "INV-1004", "direction": "inbound", "type": "call_notes", "date": "2026-07-14", "content": "Manager called Mary. She was apologetic, committed to paying by Jul 22. Payment received Jul 22.", "status": "received"},
        {"comm_id": "COM-010", "customer_id": "CUST-001", "invoice_id": "INV-1005", "direction": "outbound", "type": "email", "date": "2026-07-28", "content": "Hi Mary, friendly reminder that invoice INV-1005 for $44,100 is now past due.", "status": "sent"},
        {"comm_id": "COM-011", "customer_id": "CUST-002", "invoice_id": "INV-2003", "direction": "outbound", "type": "email", "date": "2026-06-20", "content": "Hi Robert, gentle reminder that invoice INV-2003 for $118,900 is approaching its due date.", "status": "sent"},
        {"comm_id": "COM-012", "customer_id": "CUST-002", "invoice_id": "INV-2004", "direction": "outbound", "type": "email", "date": "2026-07-25", "content": "Hi Robert, regarding the $30,000 deduction on INV-2004: our trade team has reviewed and determined this deduction is invalid. The promo agreement covers different SKUs. Please remit the remaining $30,000.", "status": "sent"},
        {"comm_id": "COM-013", "customer_id": "CUST-003", "invoice_id": "INV-3003", "direction": "inbound", "type": "call_notes", "date": "2026-06-15", "content": "David confirmed summer is always slow for their stores. Cash flow constrained June-August. Will pay when able.", "status": "received"},
        {"comm_id": "COM-014", "customer_id": "CUST-003", "invoice_id": "INV-3004", "direction": "inbound", "type": "call_notes", "date": "2026-07-15", "content": "David said same summer pattern. Expects to pay end of July or early August.", "status": "received"},
    ]
    return pd.DataFrame(comms)


def generate_documents():
    docs = [
        {"doc_id": "DOC-001", "customer_id": "CUST-001", "invoice_id": "INV-1001", "doc_type": "invoice_pdf", "file_path": "documents/INV-1001.pdf", "uploaded_date": "2026-03-01"},
        {"doc_id": "DOC-002", "customer_id": "CUST-001", "invoice_id": "INV-1002", "doc_type": "invoice_pdf", "file_path": "documents/INV-1002.pdf", "uploaded_date": "2026-04-01"},
        {"doc_id": "DOC-003", "customer_id": "CUST-001", "invoice_id": "INV-1003", "doc_type": "invoice_pdf", "file_path": "documents/INV-1003.pdf", "uploaded_date": "2026-05-01"},
        {"doc_id": "DOC-004", "customer_id": "CUST-001", "invoice_id": "INV-1004", "doc_type": "invoice_pdf", "file_path": "documents/INV-1004.pdf", "uploaded_date": "2026-06-01"},
        {"doc_id": "DOC-005", "customer_id": "CUST-001", "invoice_id": "INV-1005", "doc_type": "invoice_pdf", "file_path": "documents/INV-1005.pdf", "uploaded_date": "2026-07-01"},
        {"doc_id": "DOC-006", "customer_id": "CUST-002", "invoice_id": "INV-2001", "doc_type": "invoice_pdf", "file_path": "documents/INV-2001.pdf", "uploaded_date": "2026-03-01"},
        {"doc_id": "DOC-007", "customer_id": "CUST-002", "invoice_id": "INV-2002", "doc_type": "invoice_pdf", "file_path": "documents/INV-2002.pdf", "uploaded_date": "2026-04-01"},
        {"doc_id": "DOC-008", "customer_id": "CUST-002", "invoice_id": "INV-2002", "doc_type": "promo_agreement", "file_path": "documents/PROMO-Q1-2026.pdf", "uploaded_date": "2026-05-20"},
        {"doc_id": "DOC-009", "customer_id": "CUST-002", "invoice_id": "INV-2004", "doc_type": "promo_agreement", "file_path": "documents/PROMO-Q2-2026.pdf", "uploaded_date": "2026-07-20"},
        {"doc_id": "DOC-010", "customer_id": "CUST-003", "invoice_id": "INV-3001", "doc_type": "invoice_pdf", "file_path": "documents/INV-3001.pdf", "uploaded_date": "2026-03-01"},
        {"doc_id": "DOC-011", "customer_id": "CUST-003", "invoice_id": "INV-3003", "doc_type": "pod", "file_path": "documents/POD-INV3003.pdf", "uploaded_date": "2026-06-10"},
        {"doc_id": "DOC-012", "customer_id": "CUST-001", "invoice_id": "INV-1001", "doc_type": "statement", "file_path": "documents/STMT-CUST001-2026Q1.pdf", "uploaded_date": "2026-03-31"},
        {"doc_id": "DOC-013", "customer_id": "CUST-002", "invoice_id": "INV-2001", "doc_type": "remittance", "file_path": "documents/REM-CUST002-202604.pdf", "uploaded_date": "2026-04-14"},
    ]
    return pd.DataFrame(docs)


def generate_workflow_states():
    return pd.DataFrame(columns=[
        "workflow_id", "invoice_id", "customer_id", "status",
        "plan_json", "reasoning", "confidence", "reason_code", "last_updated"
    ])


def generate_credit_exposure():
    credit = [
        {"customer_id": "CUST-001", "credit_limit": 200000, "current_exposure": 0, "available_credit": 200000, "percentage_used": 0, "status": "HEALTHY"},
        {"customer_id": "CUST-002", "credit_limit": 1000000, "current_exposure": 0, "available_credit": 1000000, "percentage_used": 0, "status": "HEALTHY"},
        {"customer_id": "CUST-003", "credit_limit": 70000, "current_exposure": 0, "available_credit": 70000, "percentage_used": 0, "status": "HEALTHY"},
    ]
    return pd.DataFrame(credit)


def generate_system_state():
    return {
        "current_date": "2026-08-01",
        "last_cycle_date": None,
        "cycle_count": 0
    }


def main():
    print("Generating synthetic data for CPG Collections Workflow Agent...")
    print("=" * 60)

    ensure_dirs()

    # Generate all data
    datasets = {
        "customers.xlsx": generate_customers(),
        "invoices.xlsx": generate_invoices(),
        "payments.xlsx": generate_payments(),
        "promises_to_pay.xlsx": generate_promises_to_pay(),
        "disputes.xlsx": generate_disputes(),
        "activities.xlsx": generate_activities(),
        "communications.xlsx": generate_communications(),
        "documents.xlsx": generate_documents(),
        "workflow_states.xlsx": generate_workflow_states(),
        "credit_exposure.xlsx": generate_credit_exposure(),
    }

    for filename, df in datasets.items():
        filepath = DATA_DIR / filename
        df.to_excel(filepath, index=False)
        print(f"  Created {filename} ({len(df)} records)")

    # Save system state
    state = generate_system_state()
    with open(DATA_DIR / "system_state.json", "w") as f:
        json.dump(state, f, indent=2)
    print(f"  Created system_state.json (date: {state['current_date']})")

    # Clean incoming invoices folder
    incoming_dir = DATA_DIR / "incoming_invoices"
    for f in incoming_dir.iterdir():
        if f.is_file():
            f.unlink()

    # Clean emails folder
    emails_dir = DATA_DIR / "emails"
    for f in emails_dir.iterdir():
        if f.is_file():
            f.unlink()

    print()
    print("=" * 60)
    print("Data generation complete!")
    print(f"  3 customers with hierarchy (10 total entities)")
    print(f"  15 historical invoices (all closed/paid)")
    print(f"  17 payment records")
    print(f"  2 promise-to-pay records (1 honored, 1 broken)")
    print(f"  2 dispute records (both resolved)")
    print(f"  28 activity records")
    print(f"  14 communication records")
    print(f"  13 document records")
    print(f"  System date: August 1, 2026")
    print()
    print("Ready for experiments!")
    print("Drop an invoice PDF into data/incoming_invoices/ to begin.")


if __name__ == "__main__":
    main()
