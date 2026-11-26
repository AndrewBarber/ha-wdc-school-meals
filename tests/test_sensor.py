"""Today and next school day sensors, and the cycle week."""

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.models import Menu

from .conftest import child, main_entry, setup_entry

TODAY = "sensor.alex_school_meals_today"
NEXT = "sensor.alex_school_meals_next_school_day"
CYCLE = "sensor.alex_school_meals_cycle_week"


async def _setup(hass: HomeAssistant, menu: Menu = Menu.PRIMARY) -> None:
    school = "balloch-primary-school" if menu is Menu.PRIMARY else "dumbarton-academy"
    await setup_entry(hass, main_entry([child(menu, school, "Alex")]))


@pytest.mark.usefixtures("mock_wdc")
async def test_wednesday(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass)

    today = hass.states.get(TODAY)
    assert today.state == "Beef Burger in a Bun with optional Cheese or Meat Free Mince"
    assert today.attributes["friendly_name"] == "Alex's School Meals Today"
    assert today.attributes["date"] == "2026-10-28"
    assert today.attributes["cycle_week"] == 3
    assert today.attributes["closure_reason"] is None
    assert today.attributes["courses"]["Meal 2"][0] == "Meat Free Mince"
    assert "Meat Free Mince" in today.attributes["vegetarian"]
    assert (
        "Beef Burger in a Bun with optional Cheese"
        in today.attributes["contains_allergens"]
    )
    assert today.attributes["menu_url"] == Menu.PRIMARY.url

    upcoming = hass.states.get(NEXT)
    assert upcoming.state == "Chicken Goujons or Tomato & Basil Pasta"
    assert upcoming.attributes["date"] == "2026-10-29"

    assert hass.states.get(CYCLE).state == "3"
    entry = er.async_get(hass).async_get(CYCLE)
    assert entry.entity_category is er.EntityCategory.DIAGNOSTIC


@pytest.mark.usefixtures("mock_wdc")
async def test_secondary(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, Menu.SECONDARY)

    assert hass.states.get(TODAY).state == (
        "Cheese Baked Vegetarian Pasta or Bubble Salmon"
    )


@pytest.mark.usefixtures("mock_wdc")
async def test_friday_looks_to_monday(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-30 10:00:00+00:00")
    await _setup(hass)

    upcoming = hass.states.get(NEXT)
    assert upcoming.state == "Macaroni Cheese or Baked Potato with Baked Beans"
    assert upcoming.attributes["date"] == "2026-11-02"


@pytest.mark.usefixtures("mock_wdc")
async def test_weekend(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-31 10:00:00+00:00")
    await _setup(hass)

    today = hass.states.get(TODAY)
    assert today.state == "No school"
    assert today.attributes["closure_reason"] == "Weekend"
    assert hass.states.get(NEXT).attributes["date"] == "2026-11-02"


@pytest.mark.usefixtures("mock_wdc")
async def test_skips_the_in_service_day(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-06 10:00:00+00:00")
    await _setup(hass)

    upcoming = hass.states.get(NEXT)
    assert upcoming.attributes["date"] == "2026-11-10"
    assert upcoming.state == "Chicken Curry or Cheese and Tomato Pizza"


@pytest.mark.usefixtures("mock_wdc")
async def test_rolls_over_at_midnight(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 23:59:00+00:00")
    await _setup(hass)
    assert hass.states.get(TODAY).attributes["date"] == "2026-10-28"

    freezer.move_to("2026-10-29 00:00:31+00:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    # The request debouncer waits before refreshing
    freezer.tick(timedelta(seconds=15))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    today = hass.states.get(TODAY)
    assert today.attributes["date"] == "2026-10-29"
    assert today.state == "Chicken Goujons or Tomato & Basil Pasta"


async def test_unavailable_when_the_site_goes_down(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass)
    assert hass.states.get(TODAY).state != "unavailable"

    mock_wdc.clear_requests()
    mock_wdc.get(Menu.PRIMARY.url, status=503)
    # Cached weeks last 12 hours; the second 6-hourly refresh after that fetches
    freezer.tick(timedelta(hours=6, minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(TODAY).state != "unavailable"
    freezer.tick(timedelta(hours=6, minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    assert hass.states.get(TODAY).state == "unavailable"
