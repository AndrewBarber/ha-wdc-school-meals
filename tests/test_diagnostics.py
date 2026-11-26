"""Diagnostics download."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.wdc_school_meals.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.wdc_school_meals.models import Menu

from .conftest import child, main_entry, setup_entry


@pytest.mark.usefixtures("mock_wdc")
async def test_diagnostics(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    await setup_entry(hass, entry)

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["children"] == [
        {
            "title": "Alex's School Meals",
            "data": {
                "name": "Alex",
                "school": "balloch-primary-school",
                "menu": "primary",
                "watch_allergens": "**REDACTED**",
            },
        }
    ]
    primary = diag["menus"]["primary"]
    assert primary["last_update_success"] is True
    assert primary["cycle_week"] == 3
    assert primary["weeks"]["2026-10-26"] == {"label": "Primary Week 3", "days": 5}
    assert [y["first_day"] for y in diag["term_dates"]] == ["2026-08-17", "2027-08-17"]
