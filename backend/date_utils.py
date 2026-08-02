"""Date parsing helpers that do not call pandas' datetime extensions."""

from datetime import date, datetime, timezone
import math
from typing import Any


def parse_datetime(value: Any) -> datetime:
    """Return a plain, timezone-naive Python datetime for a supported value."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise ValueError("Date value is missing")

    if isinstance(value, datetime):
        # Rebuild datetime subclasses (including pandas Timestamp) as a stdlib
        # datetime without invoking their conversion methods.
        try:
            parsed = datetime(
                value.year,
                value.month,
                value.day,
                value.hour,
                value.minute,
                value.second,
                value.microsecond,
                tzinfo=value.tzinfo,
                fold=getattr(value, "fold", 0),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid date value: {value!r}") from exc
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nat", "nan", "none"}:
            raise ValueError("Date value is missing")

        # Python 3.10 and earlier do not accept the ISO-8601 Z suffix.
        if text.endswith(("Z", "z")):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO date value: {value!r}") from exc
    else:
        raise TypeError(f"Unsupported date value type: {type(value).__name__}")

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def parse_date(value: Any) -> date:
    """Return the calendar date from a supported date/datetime value."""
    return parse_datetime(value).date()
