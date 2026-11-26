"""Term dates pages and the school calendar built from them."""

from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.api import WdcClient
from custom_components.wdc_school_meals.models import BASE_URL
from custom_components.wdc_school_meals.terms import (
    NOT_LISTED,
    SUMMER_HOLIDAYS,
    TERM_DATES_PATH,
    WEEKEND,
    Closure,
    SchoolCalendar,
    TermDatesError,
    fetch_school_years,
    parse_term_dates,
    term_dates_links,
)

from .pages import load_page


@pytest.fixture
def calendar() -> SchoolCalendar:
    return SchoolCalendar(
        [
            parse_term_dates(load_page("term-date-202627.html")),
            parse_term_dates(load_page("term-dates-202728.html")),
        ]
    )


def test_parse_2026_27() -> None:
    year = parse_term_dates(load_page("term-date-202627.html"))

    assert year.first_day == date(2026, 8, 17)
    assert year.last_day == date(2027, 6, 30)
    assert (
        Closure(date(2026, 10, 12), date(2026, 10, 16), "Half-term - October Break")
        in year.closures
    )
    assert (
        Closure(date(2026, 11, 9), date(2026, 11, 9), "In-service Day") in year.closures
    )
    # "and" lists two single days, not a range
    assert (
        Closure(date(2026, 9, 25), date(2026, 9, 25), "September week-end")
        in year.closures
    )
    assert (
        Closure(date(2026, 9, 28), date(2026, 9, 28), "September week-end")
        in year.closures
    )
    # "to" is a range
    assert (
        Closure(date(2027, 3, 26), date(2027, 3, 29), "Easter public holiday")
        in year.closures
    )
    # Early closes and re-opening days are not closures
    assert not any(c.start == date(2026, 12, 18) for c in year.closures)
    assert not any(c.start == date(2027, 1, 5) for c in year.closures)


def test_parse_2027_28() -> None:
    year = parse_term_dates(load_page("term-dates-202728.html"))
    assert year.first_day == date(2027, 8, 17)
    assert year.last_day == date(2028, 6, 30)


def test_parse_rejects_a_page_without_terms() -> None:
    with pytest.raises(TermDatesError):
        parse_term_dates("<ul><li>Nothing to see: here</li></ul>")


def test_term_dates_links() -> None:
    assert term_dates_links(load_page("term-dates.html")) == [
        f"{TERM_DATES_PATH}/term-date-202627",
        f"{TERM_DATES_PATH}/term-dates-202728",
    ]
    with pytest.raises(TermDatesError):
        term_dates_links("<a href='/elsewhere'>x</a>")


@pytest.mark.parametrize(
    ("day", "reason"),
    [
        (date(2026, 10, 28), None),  # an ordinary Wednesday
        (date(2026, 10, 31), WEEKEND),
        (date(2026, 10, 13), "Half-term - October Break"),
        (date(2026, 11, 9), "In-service Day"),
        (date(2026, 12, 18), None),  # early close, lunch still served
        (date(2026, 12, 21), "Christmas/New Year Break"),
        (date(2027, 1, 4), "Christmas/New Year Break"),
        (date(2027, 1, 5), None),
        (date(2027, 6, 30), None),  # last day
        (date(2027, 7, 5), SUMMER_HOLIDAYS),
        (date(2027, 8, 17), None),  # first day of 2027/28
        (date(2026, 8, 10), SUMMER_HOLIDAYS),  # before the first known year
        (date(2028, 10, 2), NOT_LISTED),  # past every known year
    ],
)
def test_closure_reason(
    calendar: SchoolCalendar, day: date, reason: str | None
) -> None:
    assert calendar.closure_reason(day) == reason
    assert calendar.is_school_day(day) is (reason is None)


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        (date(2026, 10, 28), date(2026, 10, 29)),
        (date(2026, 10, 30), date(2026, 11, 2)),  # Friday to Monday
        (date(2026, 11, 6), date(2026, 11, 10)),  # skips the in-service Monday
        (date(2026, 10, 9), date(2026, 10, 19)),  # over the October break
        (date(2026, 12, 18), date(2027, 1, 5)),  # over Christmas
        (date(2027, 6, 30), date(2027, 8, 17)),  # over the summer
    ],
)
def test_next_school_day(calendar: SchoolCalendar, after: date, expected: date) -> None:
    assert calendar.next_school_day(after) == expected


def test_next_closure(calendar: SchoolCalendar) -> None:
    assert calendar.next_closure(date(2026, 10, 28)) == (
        date(2026, 11, 9),
        "In-service Day",
    )


def test_unknown_terms_only_skip_weekends() -> None:
    calendar = SchoolCalendar()
    assert not calendar.known
    assert calendar.is_school_day(date(2026, 10, 13))
    assert calendar.closure_reason(date(2026, 10, 31)) == WEEKEND
    assert calendar.next_school_day(date(2026, 10, 30)) == date(2026, 11, 2)


async def test_fetch_school_years(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    for page in ("term-date-202627", "term-dates-202728"):
        aioclient_mock.get(
            f"{BASE_URL}{TERM_DATES_PATH}/{page}", text=load_page(f"{page}.html")
        )
    aioclient_mock.get(
        f"{BASE_URL}{TERM_DATES_PATH}", text=load_page("term-dates.html")
    )

    years = await fetch_school_years(WdcClient(async_get_clientsession(hass)))

    assert [y.first_day for y in years] == [date(2026, 8, 17), date(2027, 8, 17)]
