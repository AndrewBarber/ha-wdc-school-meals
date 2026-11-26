"""Lunch calendar."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.wdc_school_meals.const import CONF_WEEKS_AHEAD
from custom_components.wdc_school_meals.models import Menu

from .conftest import child, main_entry, setup_entry

CALENDAR = "calendar.alex_school_meals_lunches"


async def _setup(hass: HomeAssistant, options: dict | None = None) -> None:
    await setup_entry(
        hass,
        main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")], options),
    )


async def _events(hass: HomeAssistant, start: str, end: str) -> list[dict]:
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": CALENDAR, "start_date_time": start, "end_date_time": end},
        blocking=True,
        return_response=True,
    )
    return response[CALENDAR]["events"]


@pytest.mark.usefixtures("mock_wdc")
async def test_state_is_todays_lunch(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass)

    state = hass.states.get(CALENDAR)
    assert state.state == "on"
    assert state.attributes["friendly_name"] == "Alex's School Meals Lunches"
    assert state.attributes["message"] == (
        "Beef Burger in a Bun with optional Cheese or Meat Free Mince"
    )
    assert state.attributes["all_day"] is True


@pytest.mark.usefixtures("mock_wdc")
async def test_weekend_points_at_monday(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-31 10:00:00+00:00")
    await _setup(hass)

    state = hass.states.get(CALENDAR)
    assert state.state == "off"
    assert state.attributes["start_time"] == "2026-11-02 00:00:00"


@pytest.mark.usefixtures("mock_wdc")
async def test_three_weeks_skip_the_in_service_day(
    hass: HomeAssistant, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass)

    events = await _events(
        hass, "2026-10-26T00:00:00+00:00", "2026-11-16T00:00:00+00:00"
    )

    days = [event["start"] for event in events]
    assert len(days) == 14
    assert days[0] == "2026-10-26"
    assert "2026-11-09" not in days
    assert days[-1] == "2026-11-13"
    monday = events[0]
    assert monday["summary"] == "Vegetable Curry or Macaroni Cheese"
    assert (
        "Meal 1: Vegetable Curry, Boiled Rice, Peas, Salad Bar" in monday["description"]
    )


@pytest.mark.usefixtures("mock_wdc")
async def test_weeks_ahead_option_limits_the_range(
    hass: HomeAssistant, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, {CONF_WEEKS_AHEAD: 1})

    events = await _events(
        hass, "2026-10-26T00:00:00+00:00", "2026-11-16T00:00:00+00:00"
    )

    assert events[-1]["start"] == "2026-11-06"


@pytest.mark.usefixtures("mock_wdc")
async def test_holidays_have_no_lunches(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-12-29 10:00:00+00:00")
    await _setup(hass)

    # The site lists menus over Christmas, but school is shut until 5 January
    events = await _events(
        hass, "2026-12-28T00:00:00+00:00", "2027-01-09T00:00:00+00:00"
    )

    assert [event["start"] for event in events] == [
        "2027-01-05",
        "2027-01-06",
        "2027-01-07",
        "2027-01-08",
    ]


async def test_a_failing_week_is_skipped(
    hass: HomeAssistant, mock_wdc, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass)
    mock_wdc.clear_requests()
    mock_wdc.get(Menu.PRIMARY.url, status=503)

    # Five weeks back is outside the cache, so it has to be fetched and fails
    events = await _events(
        hass, "2026-09-21T00:00:00+01:00", "2026-09-26T00:00:00+01:00"
    )

    assert events == []
