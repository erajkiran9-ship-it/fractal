import unittest
from unittest.mock import patch

from backend.routes.notifications import get_dispute_notifications


class NotificationFeedTests(unittest.TestCase):
    @patch("backend.routes.notifications.db.get_customer")
    @patch("backend.routes.notifications.db.get_dispute")
    @patch("backend.routes.notifications.db.get_all_disputes")
    @patch("backend.routes.notifications.db.get_all_activities")
    def test_two_same_day_disputes_create_two_independent_notifications(
        self,
        get_all_activities,
        get_all_disputes,
        get_dispute,
        get_customer,
    ):
        disputes = {
            "DSP-101": {
                "dispute_id": "DSP-101",
                "customer_id": "CUST-001",
                "invoice_id": "INV-101",
                "status": "OPEN",
                "created_date": "2026-08-10",
            },
            "DSP-202": {
                "dispute_id": "DSP-202",
                "customer_id": "CUST-002",
                "invoice_id": "INV-202",
                "status": "OPEN",
                "created_date": "2026-08-10",
            },
        }
        get_all_activities.return_value = [
            {
                "activity_id": "ACT-101",
                "customer_id": "CUST-001",
                "invoice_id": "INV-101",
                "type": "dispute_raised",
                "date": "2026-08-10",
                "details": "First dispute",
                "outcome": "DSP-101",
            },
            {
                "activity_id": "ACT-202",
                "customer_id": "CUST-002",
                "invoice_id": "INV-202",
                "type": "dispute_raised",
                "date": "2026-08-10",
                "details": "Second dispute",
                "outcome": "DSP-202",
            },
        ]
        get_all_disputes.return_value = list(disputes.values())
        get_dispute.side_effect = disputes.get
        get_customer.side_effect = lambda customer_id: {
            "name": f"Customer {customer_id[-3:]}"
        }

        response = get_dispute_notifications("2026-08-10")

        self.assertEqual(response["count"], 2)
        self.assertEqual(
            {item["dispute_id"] for item in response["notifications"]},
            {"DSP-101", "DSP-202"},
        )
        self.assertEqual(
            {item["target_url"] for item in response["notifications"]},
            {"/disputes/case/DSP-101", "/disputes/case/DSP-202"},
        )


if __name__ == "__main__":
    unittest.main()
