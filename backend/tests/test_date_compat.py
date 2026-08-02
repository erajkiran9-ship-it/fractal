import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from backend.agent.tools import _handle_get_new_events, _handle_get_open_invoices
from backend.data_layer import excel_store
from backend.date_utils import parse_date, parse_datetime
from backend.routes import invoices, simulation


class FakeDataFrame:
    def __init__(self, records):
        self._records = records
        self.empty = not records

    def to_dict(self, orient):
        if orient != "records":
            raise AssertionError(f"Unexpected orientation: {orient}")
        return [record.copy() for record in self._records]


class DateUtilsTests(unittest.TestCase):
    def test_parses_stdlib_and_iso_values(self):
        self.assertEqual(parse_date("2026-08-01"), date(2026, 8, 1))
        self.assertEqual(parse_date(datetime(2026, 8, 2, 12)), date(2026, 8, 2))
        self.assertEqual(parse_datetime("2026-08-01T04:30:00Z"), datetime(2026, 8, 1, 4, 30))

    def test_normalizes_aware_values_to_naive_utc(self):
        value = datetime(2026, 8, 1, 4, 30, tzinfo=timezone.utc)
        self.assertEqual(parse_datetime(value), datetime(2026, 8, 1, 4, 30))

    def test_rejects_missing_values(self):
        for value in (None, "", "NaT", float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_datetime(value)


class ExcelStoreDateFilteringTests(unittest.TestCase):
    def test_filters_records_using_python_datetimes(self):
        frame = FakeDataFrame([
            {"payment_id": "old", "date": "2026-07-31"},
            {"payment_id": "boundary", "date": "2026-08-01"},
            {"payment_id": "new", "date": datetime(2026, 8, 2, 9)},
            {"payment_id": "missing", "date": ""},
        ])

        with patch.object(excel_store, "_read_excel", return_value=frame):
            result = excel_store.get_new_payments_since("2026-08-01")

        self.assertEqual([row["payment_id"] for row in result], ["boundary", "new"])
        self.assertTrue(all(type(row["date"]) is datetime for row in result))

    def test_inbound_filter_applies_direction_and_date(self):
        frame = FakeDataFrame([
            {"comm_id": "in", "direction": "inbound", "date": "2026-08-01"},
            {"comm_id": "out", "direction": "outbound", "date": "2026-08-02"},
        ])

        with patch.object(excel_store, "_read_excel", return_value=frame):
            result = excel_store.get_new_inbound_since("2026-08-01")

        self.assertEqual([row["comm_id"] for row in result], ["in"])


class BusinessDatePathTests(unittest.TestCase):
    def test_agent_open_invoice_aging(self):
        rows = [{"invoice_id": "INV-1", "due_date": "2026-06-15"}]
        with patch.object(excel_store, "get_open_invoices", return_value=rows):
            result = _handle_get_open_invoices({}, "2026-08-01")

        self.assertEqual(result["open_invoices"][0]["days_overdue"], 47)
        self.assertEqual(result["open_invoices"][0]["aging_bucket"], "31-60")

    def test_ptp_deadline_event_uses_python_date_arithmetic(self):
        ptp = {
            "ptp_id": "PTP-1",
            "customer_id": "CUST-1",
            "invoice_id": "INV-1",
            "promise_date": "2026-07-29",
            "amount": 100,
        }
        patches = (
            patch.object(excel_store, "get_system_state", return_value={"last_cycle_date": "2026-08-01"}),
            patch.object(excel_store, "get_new_payments_since", return_value=[]),
            patch.object(excel_store, "get_new_inbound_since", return_value=[]),
            patch.object(excel_store, "get_new_activities_since", return_value=[]),
            patch.object(excel_store, "get_active_ptps", return_value=[ptp]),
            patch.object(excel_store, "get_payments_by_invoice", return_value=[]),
            patch.object(excel_store, "get_all_credit_exposure", return_value=[]),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            result = _handle_get_new_events({}, "2026-08-01")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["events"][0]["type"], "ptp_deadline_passed")

    def test_invoice_route_aging(self):
        rows = [{"invoice_id": "INV-1", "due_date": "2026-07-31"}]
        with (
            patch.object(excel_store, "get_open_invoices", return_value=rows),
            patch.object(excel_store, "get_system_state", return_value={"current_date": "2026-08-01"}),
        ):
            result = invoices.get_open_invoices()

        self.assertEqual(result["invoices"][0]["days_overdue"], 1)

    def test_simulation_aging_summary(self):
        rows = [
            {"due_date": "2026-08-10", "amount": 50, "amount_paid": 0},
            {"due_date": "2026-07-01", "amount": 100, "amount_paid": 25},
        ]
        with (
            patch.object(excel_store, "get_open_invoices", return_value=rows),
            patch.object(excel_store, "get_system_state", return_value={"current_date": "2026-08-01"}),
        ):
            result = simulation.get_aging_summary()

        self.assertEqual(result["aging"]["current"], 50)
        self.assertEqual(result["aging"]["31-60"], 75)
        self.assertEqual(result["total"], 125)

    def test_advance_three_days_runs_cycle_on_target_date(self):
        state = {"current_date": "2026-08-01", "cycle_count": 4}
        agent_result = {"date": "2026-08-04", "status": "completed"}
        with (
            patch.object(excel_store, "get_system_state", return_value=state),
            patch.object(excel_store, "save_system_state") as save_state,
            patch.object(simulation, "run_daily_cycle", return_value=agent_result) as run_cycle,
            patch.object(simulation, "missing_configuration", return_value=[]),
        ):
            result = simulation.advance_three_days()

        self.assertEqual(result["new_date"], "2026-08-04")
        self.assertEqual(result["days_advanced"], 3)
        self.assertEqual(result["agent_result"], agent_result)
        save_state.assert_called_once_with(
            {"current_date": "2026-08-04", "cycle_count": 4}
        )
        run_cycle.assert_called_once_with("2026-08-04")

    def test_missing_model_key_does_not_advance_simulation(self):
        state = {"current_date": "2026-08-01", "cycle_count": 4}
        with (
            patch.object(excel_store, "get_system_state", return_value=state),
            patch.object(excel_store, "save_system_state") as save_state,
            patch.object(simulation, "run_daily_cycle") as run_cycle,
            patch.object(
                simulation,
                "missing_configuration",
                return_value=["AZURE_OPENAI_API_KEY"],
            ),
        ):
            result = simulation.advance_three_days()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["new_date"], "2026-08-01")
        self.assertEqual(result["days_advanced"], 0)
        save_state.assert_not_called()
        run_cycle.assert_not_called()

    def test_provider_error_rolls_back_attempted_date(self):
        state = {"current_date": "2026-08-01", "cycle_count": 0}
        agent_result = {
            "date": "2026-08-04",
            "status": "error",
            "agent_reasoning": "API Error: unauthorized",
        }
        with (
            patch.object(excel_store, "get_system_state", return_value=state),
            patch.object(excel_store, "save_system_state") as save_state,
            patch.object(simulation, "run_daily_cycle", return_value=agent_result),
            patch.object(simulation, "missing_configuration", return_value=[]),
        ):
            result = simulation.advance_three_days()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["new_date"], "2026-08-01")
        self.assertEqual(result["attempted_date"], "2026-08-04")
        self.assertEqual(result["days_advanced"], 0)
        self.assertEqual(save_state.call_count, 2)
        self.assertEqual(save_state.call_args.args[0]["current_date"], "2026-08-01")


if __name__ == "__main__":
    unittest.main()
