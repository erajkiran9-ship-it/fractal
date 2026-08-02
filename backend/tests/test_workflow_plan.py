import json
import unittest

from backend.workflow_plan import (
    WorkflowPlanError,
    parse_workflow_plan,
    serialize_workflow_plan,
)


class WorkflowPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "scheduled_actions": [
                {"action": "send_pre_due_reminder", "date": "2026-08-15"}
            ],
            "completed_actions": [],
            "flags": ["mid_tier_segment"],
        }

    def test_parses_canonical_json(self):
        self.assertEqual(parse_workflow_plan(json.dumps(self.plan)), self.plan)

    def test_parses_nested_quote_escaped_legacy_json(self):
        escaped = json.dumps(json.dumps(self.plan).replace('"', r'\"'))
        self.assertEqual(parse_workflow_plan(escaped), self.plan)

    def test_serializes_nested_input_once(self):
        nested = json.dumps(json.dumps(self.plan))
        serialized = serialize_workflow_plan(nested)
        self.assertEqual(json.loads(serialized), self.plan)
        self.assertFalse(serialized.startswith('"'))

    def test_rejects_invalid_plan(self):
        with self.assertRaises(WorkflowPlanError):
            parse_workflow_plan("{not valid json}")


if __name__ == "__main__":
    unittest.main()
