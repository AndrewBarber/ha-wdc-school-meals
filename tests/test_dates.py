"""Date helpers: the heading's date range, the menu week and the cycle week.

Ported from the original wdc_school_menu tests.
"""

from datetime import date

import pytest

from custom_components.wdc_school_meals.dates import (
    cycle_week_number,
    monday_of,
    parse_date_range,
    week_start_from_range,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # As on the page on 2026-10-27
        ("26th - 31st October 2026", (date(2026, 10, 26), date(2026, 10, 31))),
        # Across a month end
        (
            "28th September - 3rd October 2026",
            (date(2026, 9, 28), date(2026, 10, 3)),
        ),
        # Across a year end, with and without the first year
        (
            "28th December 2026 - 2nd January 2027",
            (date(2026, 12, 28), date(2027, 1, 2)),
        ),
        (
            "28th December - 2nd January 2027",
            (date(2026, 12, 28), date(2027, 1, 2)),
        ),
        # No ordinals, en dash, abbreviated month, extra spaces
        ("2 – 7 November 2026", (date(2026, 11, 2), date(2026, 11, 7))),
        ("2nd-7th Nov 2026", (date(2026, 11, 2), date(2026, 11, 7))),
        # Embedded in the heading text
        (
            "This weeks menu : Primary Week 3 26th - 31st October 2026",
            (date(2026, 10, 26), date(2026, 10, 31)),
        ),
    ],
)
def test_parse_date_range(text: str, expected: tuple[date, date]) -> None:
    assert parse_date_range(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "Primary Week 3",
        "30th - 31st February 2026",  # not a real date
        "26th - 31st Octember 2026",  # not a month
        "31st - 26th October 2026",  # ends before it starts
    ],
)
def test_parse_date_range_rejects(text: str | None) -> None:
    assert parse_date_range(text) is None


@pytest.mark.parametrize(
    ("start", "monday"),
    [
        (date(2026, 10, 26), date(2026, 10, 26)),  # Monday: itself
        (date(2026, 10, 28), date(2026, 10, 26)),  # Wednesday: back to Monday
        (date(2026, 10, 24), date(2026, 10, 26)),  # Saturday: next Monday
        (date(2026, 10, 25), date(2026, 10, 26)),  # Sunday: next Monday
    ],
)
def test_week_start_from_range(start: date, monday: date) -> None:
    assert week_start_from_range(start) == monday


@pytest.mark.parametrize(
    ("day", "monday"),
    [
        (date(2026, 10, 26), date(2026, 10, 26)),  # Monday
        (date(2026, 10, 30), date(2026, 10, 26)),  # Friday
        (date(2026, 11, 1), date(2026, 10, 26)),  # Sunday stays in its week
        (date(2027, 1, 1), date(2026, 12, 28)),  # across a year end
    ],
)
def test_monday_of(day: date, monday: date) -> None:
    assert monday_of(day) == monday


@pytest.mark.parametrize(
    ("label", "number"),
    [
        ("Primary Week 3", 3),
        ("Kilpatrick High Week 2", 2),
        ("primary week 1", 1),
        ("Menu", None),
        (None, None),
    ],
)
def test_cycle_week_number(label: str | None, number: int | None) -> None:
    assert cycle_week_number(label) == number
