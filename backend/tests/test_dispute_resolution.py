import unittest
from unittest.mock import patch

from backend.data_layer import excel_store as db
from backend.routes.disputes import DisputeResolution, resolve_dispute


class DisputeResolutionTests(unittest.TestCase):
    def setUp(self):
        self.dispute = {
            "dispute_id": "DSP-100",
            "customer_id": "CUST-100",
            "invoice_id": "INV-100",
            "type": "pricing_dispute",
            "amount": 400.0,
            "status": "UNDER_REVIEW",
            "investigation_notes": "Initial review",
        }
        self.invoice = {
            "invoice_id": "INV-100",
            "customer_id": "CUST-100",
            "amount": 1000.0,
            "amount_paid": 100.0,
            "due_date": "2026-07-01",
            "status": "DISPUTED",
        }

    def _patches(self, invoice=None):
        return (
            patch.object(db, "get_dispute", return_value=self.dispute.copy()),
            patch.object(db, "get_invoice", return_value=(invoice or self.invoice).copy()),
            patch.object(db, "get_system_state", return_value={"current_date": "2026-08-01"}),
            patch.object(db, "update_dispute"),
            patch.object(db, "update_invoice"),
            patch.object(db, "add_communication"),
            patch.object(db, "add_activity"),
            patch.object(db, "next_id", side_effect=["COM-100", "ACT-100"]),
            patch.object(db, "get_workflow_by_invoice", return_value={"workflow_id": "WF-100"}),
            patch.object(db, "update_workflow"),
        )

    def test_acceptance_closes_invoice_when_adjustment_clears_balance(self):
        invoice = {**self.invoice, "amount_paid": 600.0}
        patches = self._patches(invoice)
        with patches[0], patches[1], patches[2], patches[3] as update_dispute, \
             patches[4] as update_invoice, patches[5], patches[6], patches[7], \
             patches[8], patches[9] as update_workflow:
            result = resolve_dispute(
                "DSP-100",
                DisputeResolution(
                    decision="accepted",
                    response="The pricing claim was validated and approved.",
                ),
            )

        self.assertEqual(result["remaining_balance"], 0)
        self.assertEqual(result["invoice_status"], "CLOSED")
        update_invoice.assert_called_once_with(
            "INV-100", {"status": "CLOSED", "amount": 600.0}
        )
        self.assertEqual(update_dispute.call_args.args[1]["decision"], "ACCEPTED")
        self.assertEqual(update_workflow.call_args.args[1]["status"], "closed")

    def test_partial_acceptance_adjusts_and_resumes_remaining_balance(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], \
             patches[4] as update_invoice, patches[5], patches[6], patches[7], \
             patches[8], patches[9] as update_workflow:
            result = resolve_dispute(
                "DSP-100",
                DisputeResolution(
                    decision="partially_accepted",
                    approved_amount=150,
                    response="We approved $150 and the remaining balance is payable.",
                    notes="Validated one line-item variance.",
                ),
            )

        self.assertEqual(result["remaining_balance"], 750)
        self.assertEqual(result["invoice_status"], "OVERDUE")
        update_invoice.assert_called_once_with(
            "INV-100", {"status": "OVERDUE", "amount": 850.0}
        )
        self.assertEqual(update_workflow.call_args.args[1]["status"], "active_overdue")

    def test_rejection_resumes_full_outstanding_balance(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], \
             patches[4] as update_invoice, patches[5], patches[6], patches[7], \
             patches[8], patches[9]:
            result = resolve_dispute(
                "DSP-100",
                DisputeResolution(
                    decision="rejected",
                    response="The invoice matches the approved price list.",
                ),
            )

        self.assertEqual(result["approved_amount"], 0)
        self.assertEqual(result["remaining_balance"], 900)
        update_invoice.assert_called_once_with("INV-100", {"status": "OVERDUE"})

    def test_information_request_keeps_collection_paused(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3] as update_dispute, \
             patches[4] as update_invoice, patches[5], patches[6], patches[7], \
             patches[8], patches[9] as update_workflow:
            result = resolve_dispute(
                "DSP-100",
                DisputeResolution(
                    decision="more_information_required",
                    response="Please provide the signed purchase order.",
                    notes="Purchase order is missing.",
                ),
            )

        self.assertEqual(result["status"], "needs_information")
        self.assertEqual(update_dispute.call_args.args[1]["status"], "NEEDS_INFORMATION")
        update_invoice.assert_not_called()
        self.assertEqual(update_workflow.call_args.args[1]["status"], "paused_dispute")


if __name__ == "__main__":
    unittest.main()
