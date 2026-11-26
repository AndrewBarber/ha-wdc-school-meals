"""Date helpers for the menu page heading. No Home Assistant imports.

The heading carries the week as a range, e.g. "26th - 31st October 2026"
(Monday to Saturday), or "28th December - 2nd January 2027" across a year end.
Ported from the original wdc_school_menu, with its tests.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

MONTHS = {
    name: number
    for number, full in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        start=1,
    )
    for name in (full, full[:3], full[:4])  # "sept" as well as "sep"
}

# "26th - 31st October 2026", "28th September - 3rd October 2026",
# "28th December 2026 - 2nd January 2027", hyphen or en dash.
DATE_RANGE_RE = re.compile(
    r"\b(?P<d1>\d{1,2})(?:st|nd|rd|th)?"
    r"(?:\s+(?P<m1>[A-Za-z]+))?"
    r"(?:\s+(?P<y1>\d{4}))?"
    r"\s*[-–]\s*"
    r"(?P<d2>\d{1,2})(?:st|nd|rd|th)?\s+(?P<m2>[A-Za-z]+)\s+(?P<y2>\d{4})\b"
)

CYCLE_WEEK_RE = re.compile(r"\bWeek\s+(\d+)\b", re.I)


def parse_date_range(text: str | None) -> tuple[date, date] | None:
    """Parse the first date range in text into (first, last) dates."""
    if not text:
        return None
    m = DATE_RANGE_RE.search(text)
    if not m:
        return None
    end_month = MONTHS.get(m["m2"].lower())
    start_month = MONTHS.get(m["m1"].lower()) if m["m1"] else end_month
    if end_month is None or start_month is None:
        return None
    end_year = int(m["y2"])
    if m["y1"]:
        start_year = int(m["y1"])
    else:
        start_year = end_year - 1 if start_month > end_month else end_year
    try:
        start = date(start_year, start_month, int(m["d1"]))
        end = date(end_year, end_month, int(m["d2"]))
    except ValueError:
        return None
    if end < start:
        return None
    return start, end


def monday_of(day: date) -> date:
    """Monday of the calendar week that holds day."""
    return day - timedelta(days=day.weekday())


def week_start_from_range(start: date) -> date:
    """Monday of the school week a range starting on start covers.

    A range starting at the weekend belongs to the following week.
    """
    if start.weekday() >= 5:
        return start + timedelta(days=7 - start.weekday())
    return monday_of(start)


def cycle_week_number(label: str | None) -> int | None:
    """3 for "Primary Week 3" or "Kilpatrick High Week 3", else None."""
    if not label:
        return None
    m = CYCLE_WEEK_RE.search(label)
    return int(m.group(1)) if m else None
