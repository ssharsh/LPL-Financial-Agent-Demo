"""Calendar-month helpers. Months are (year, month) tuples."""

import calendar
import re
from collections.abc import Iterator
from datetime import date

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

Month = tuple[int, int]


def parse_month(text: str) -> Month:
    """Parse 'YYYY-MM'. Raises ValueError naming the expected format."""
    if not isinstance(text, str) or not _MONTH_RE.match(text):
        raise ValueError(f"Month must be in YYYY-MM format, got {text!r}")
    year, month = text.split("-")
    return int(year), int(month)


def format_month(month: Month) -> str:
    return f"{month[0]:04d}-{month[1]:02d}"


def parse_iso_date(text: str) -> date:
    """Parse 'YYYY-MM-DD'. Raises ValueError naming the expected format."""
    if not isinstance(text, str) or not _DATE_RE.match(text):
        raise ValueError(f"Date must be in YYYY-MM-DD format, got {text!r}")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Date {text!r} is not a valid calendar date") from exc


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def month_end(year: int, month: int) -> date:
    return date(year, month, days_in_month(year, month))


def prev_month(month: Month) -> Month:
    year, m = month
    return (year - 1, 12) if m == 1 else (year, m - 1)


def next_month(month: Month) -> Month:
    year, m = month
    return (year + 1, 1) if m == 12 else (year, m + 1)


def iter_months(start: Month, end: Month) -> Iterator[Month]:
    """Yield every month from start through end inclusive (nothing if start > end)."""
    current = start
    while current <= end:
        yield current
        current = next_month(current)


def is_month_end(day: date) -> bool:
    return day.day == days_in_month(day.year, day.month)
