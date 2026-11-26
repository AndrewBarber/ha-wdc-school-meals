"""Menu weeks are cached, reused by refreshes, and pruned."""

from datetime import date, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.models import Menu

from .conftest import child, main_entry, setup_entry


def _menu_calls(mock: AiohttpClientMocker) -> list[str]:
    return [str(url) for _, url, _, _ in mock.mock_calls if "date=" in str(url)]


async def _tick(hass: HomeAssistant, freezer, delta: timedelta) -> None:
    freezer.tick(delta)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def _setup(hass: HomeAssistant) -> None:
    await setup_entry(
        hass, main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    )


async def test_refreshes_reuse_cached_weeks(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 08:00:00+00:00")
    await _setup(hass)
    assert len(_menu_calls(mock_wdc)) == 2  # this week and next

    await _tick(hass, freezer, timedelta(hours=6, minutes=1))
    assert len(_menu_calls(mock_wdc)) == 2  # 6 hours on: from the cache

    await _tick(hass, freezer, timedelta(hours=6, minutes=1))
    assert len(_menu_calls(mock_wdc)) == 4  # past 12 hours: fetched again


async def test_midnight_within_a_week_fetches_nothing(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 23:00:00+00:00")
    await _setup(hass)
    before = len(_menu_calls(mock_wdc))

    freezer.move_to("2026-10-29 00:00:31+00:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    await _tick(hass, freezer, timedelta(seconds=15))  # request debouncer

    state = hass.states.get("sensor.alex_school_meals_today")
    assert state.attributes["date"] == "2026-10-29"
    assert len(_menu_calls(mock_wdc)) == before


async def test_old_weeks_are_dropped(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    await setup_entry(hass, entry)
    coordinator = entry.runtime_data.coordinators[Menu.PRIMARY]
    stale = date(2026, 9, 7)  # seven weeks back
    coordinator._weeks[stale] = (dt_util.utcnow(), None)

    await coordinator.async_refresh()

    assert stale not in coordinator._weeks
    assert date(2026, 10, 26) in coordinator._weeks
