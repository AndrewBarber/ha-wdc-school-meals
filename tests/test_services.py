"""The get_menu action."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.const import DOMAIN
from custom_components.wdc_school_meals.models import Menu

from .conftest import child, main_entry, setup_entry

TODAY = "sensor.alex_school_meals_today"


async def _get_menu(hass: HomeAssistant, **data) -> dict:
    return await hass.services.async_call(
        DOMAIN, "get_menu", data, blocking=True, return_response=True
    )


@pytest.fixture
async def alex(hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await setup_entry(
        hass, main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    )


@pytest.mark.usefixtures("alex")
async def test_today(hass: HomeAssistant) -> None:
    response = await _get_menu(hass, entity_id=TODAY)

    assert response["date"] == "2026-10-28"
    assert response["child"] == "Alex's School Meals"
    assert response["menu"] == "Primary"
    assert response["school_day"] is True
    assert response["cycle_week"] == 3
    assert response["summary"] == (
        "Beef Burger in a Bun with optional Cheese or Meat Free Mince"
    )
    assert response["courses"]["Drinks"] == ["Water", "Milk"]


@pytest.mark.usefixtures("alex")
async def test_another_date_from_the_calendar_entity(hass: HomeAssistant) -> None:
    response = await _get_menu(
        hass, entity_id="calendar.alex_school_meals_lunches", date="2026-11-10"
    )
    assert response["summary"] == "Chicken Curry or Cheese and Tomato Pizza"
    assert response["cycle_week"] == 2


@pytest.mark.usefixtures("alex")
async def test_closed_day(hass: HomeAssistant) -> None:
    response = await _get_menu(hass, entity_id=TODAY, date="2026-11-09")

    assert response["school_day"] is False
    assert response["closure_reason"] == "In-service Day"
    assert response["summary"] is None
    assert "courses" not in response


@pytest.mark.usefixtures("alex")
async def test_not_one_of_ours(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.kitchen_temperature", "21")
    with pytest.raises(ServiceValidationError) as err:
        await _get_menu(hass, entity_id="sensor.kitchen_temperature")
    assert err.value.translation_key == "not_a_child_entity"


@pytest.mark.usefixtures("alex")
async def test_entry_not_loaded(hass: HomeAssistant) -> None:
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as err:
        await _get_menu(hass, entity_id=TODAY)
    assert err.value.translation_key == "not_loaded"


async def test_site_down(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await setup_entry(
        hass, main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    )
    mock_wdc.clear_requests()
    mock_wdc.get(Menu.PRIMARY.url, status=503)

    with pytest.raises(HomeAssistantError) as err:
        await _get_menu(hass, entity_id=TODAY, date="2026-12-01")
    assert err.value.translation_key == "menu_unavailable"
