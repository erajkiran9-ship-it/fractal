"""Canonical parsing and serialization for agent-generated workflow plans."""

import json
from collections.abc import Mapping
from typing import Any


class WorkflowPlanError(ValueError):
    """Raised when a workflow plan cannot be normalized to an object."""


def parse_workflow_plan(value: Any) -> dict:
    """Decode normal, nested, and legacy quote-escaped workflow plans."""
    parsed = value
    for _ in range(5):
        if isinstance(parsed, Mapping):
            return dict(parsed)
        if not isinstance(parsed, str):
            raise WorkflowPlanError(
                f"Workflow plan must be an object, got {type(parsed).__name__}"
            )

        text = parsed.strip()
        if not text:
            return {}

        try:
            parsed = json.loads(text)
            continue
        except json.JSONDecodeError:
            # Older Gemini tool calls sometimes wrapped JSON as a string and
            # escaped every structural quote (for example: {\"actions\": []}).
            if text.startswith((r'{\"', r'[\"')):
                parsed = text.replace(r'\"', '"')
                continue
            raise WorkflowPlanError("Workflow plan contains invalid JSON")

    raise WorkflowPlanError("Workflow plan is nested too deeply")


def serialize_workflow_plan(value: Any) -> str:
    """Serialize a workflow plan exactly once in canonical JSON form."""
    return json.dumps(parse_workflow_plan(value), separators=(",", ":"))
