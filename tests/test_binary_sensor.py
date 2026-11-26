"""School day sensor."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.wdc_school_meals.models import Menu

from .conftest import child, main_entry, setup_entry

SCHOOL_DAY = "binary_sensor.alex_school_meals_school_day"


async def _setup(hass: HomeAssistant) -> None:
    await setup_entry(
        hass, main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    )


@pytest.mark.usefixtures("mock_wdc")
async def test_open(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass)

    state = hass.states.get(SCHOOL_DAY)
    assert state.state == "on"
    assert state.attributes["closure_reason"] is None
    assert state.attributes["next_school_day"] == "2026-10-29"
    assert state.attributes["next_closure"] == "2026-11-09"
    assert state.attributes["next_closure_reason"] == "In-service Day"
    assert state.attributes["term_dates_known"] is True


@pytest.mark.usefixtures("mock_wdc")
async def test_in_service_day(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-09 10:00:00+00:00")
    await _setup(hass)

    state = hass.states.get(SCHOOL_DAY)
    assert state.state == "off"
    assert state.attributes["closure_reason"] == "In-service Day"
    assert hass.states.get("sensor.alex_school_meals_today").state == "No school"
