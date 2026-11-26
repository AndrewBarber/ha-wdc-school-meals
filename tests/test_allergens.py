"""The allergens option: dish pages fetched, cached and shown."""

import re
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.const import CONF_ALLERGENS
from custom_components.wdc_school_meals.coordinator import DISH_STORE_KEY
from custom_components.wdc_school_meals.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.wdc_school_meals.models import Menu

from .conftest import MEALS, child, main_entry, setup_entry

TODAY = "sensor.alex_school_meals_today"
CALENDAR = "calendar.alex_school_meals_lunches"


def _dish_calls(mock: AiohttpClientMocker) -> list[str]:
    return [str(url) for _, url, _, _ in mock.mock_calls if "/meals/" in str(url)]


async def _setup(hass: HomeAssistant, allergens: bool) -> None:
    await setup_entry(
        hass,
        main_entry(
            [child(Menu.PRIMARY, "balloch-primary-school", "Alex")],
            {CONF_ALLERGENS: allergens},
        ),
    )


async def test_off_by_default(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, allergens=False)

    assert "allergens" not in hass.states.get(TODAY).attributes
    assert _dish_calls(mock_dishes) == []


async def test_named_allergens(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, hass_storage, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, allergens=True)

    attrs = hass.states.get(TODAY).attributes
    assert attrs["allergens"]["Beef Burger in a Bun with optional Cheese"] == [
        "Wheat",
        "Gluten",
        "Soya",
        "Sulphite",
        "Sesame",
        "Milk",
    ]
    # Dishes with no allergens are left out
    assert "Sweetcorn" not in attrs["allergens"]
    # Only dishes on today's and tomorrow's menus, each once
    calls = _dish_calls(mock_dishes)
    assert len(calls) == len(set(calls))
    assert all("water" not in call for call in calls)

    # Saved for next time, after the store's short delay
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()
    saved = hass_storage[DISH_STORE_KEY]["data"]["dishes"]
    assert f"{MEALS}/main/beef-burger-in-a-bun-with-cheese" in saved


async def test_cached_dishes_are_not_fetched_again(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, allergens=True)
    first = len(_dish_calls(mock_dishes))

    freezer.tick(timedelta(hours=6, minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    assert len(_dish_calls(mock_dishes)) == first


async def test_calendar_description_names_allergens(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, allergens=True)

    state = hass.states.get(CALENDAR)
    assert (
        "Beef Burger in a Bun with optional Cheese (Wheat, Gluten, Soya, Sulphite, "
        "Sesame, Milk)" in state.attributes["description"]
    )


async def test_loads_saved_dishes(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, hass_storage, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    burger = f"{MEALS}/main/beef-burger-in-a-bun-with-cheese"
    hass_storage[DISH_STORE_KEY] = {
        "version": 1,
        "key": DISH_STORE_KEY,
        "data": {
            "dishes": {
                burger: {
                    "fetched": "2026-10-27T10:00:00+00:00",
                    "dish": {
                        "url": burger,
                        "name": "Beef Burger in a Bun with optional Cheese",
                        "vegetarian": False,
                        "allergens": ["Saved"],
                        "ingredients": [],
                    },
                }
            }
        },
    }
    # Every other dish fails, and is skipped
    mock_wdc.get(re.compile(re.escape(MEALS) + "/.*"), status=500)
    await _setup(hass, allergens=True)

    attrs = hass.states.get(TODAY).attributes
    assert attrs["allergens"] == {
        "Beef Burger in a Bun with optional Cheese": ["Saved"]
    }
    assert burger not in _dish_calls(mock_wdc)


async def test_removing_the_entry_deletes_saved_dishes(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, hass_storage, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, allergens=True)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()
    assert DISH_STORE_KEY in hass_storage

    entry = hass.config_entries.async_entries("wdc_school_meals")[0]
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert DISH_STORE_KEY not in hass_storage


async def test_get_menu_names_allergens(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, allergens=True)

    response = await hass.services.async_call(
        "wdc_school_meals",
        "get_menu",
        {"entity_id": TODAY, "date": "2026-11-02"},
        blocking=True,
        return_response=True,
    )

    assert response["allergens"]["Macaroni Cheese"] == ["Gluten", "Wheat", "Milk"]


async def test_diagnostics_count_cached_dishes(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, allergens=True)
    entry = hass.config_entries.async_entries("wdc_school_meals")[0]

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["dishes_cached"] > 0
