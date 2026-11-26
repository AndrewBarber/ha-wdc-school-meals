"""HTTP client: query string, empty weeks and errors."""

from datetime import date

import pytest
from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.api import WdcClient, WdcConnectionError
from custom_components.wdc_school_meals.models import Menu

from .pages import load_page


async def test_fetch_week_asks_for_the_monday(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        f"{Menu.PRIMARY.url}?date=26-10-2026",
        text=load_page("primary-menus-26-10-2026.html"),
    )
    client = WdcClient(async_get_clientsession(hass))

    week = await client.fetch_week(Menu.PRIMARY, date(2026, 10, 29))

    assert week is not None
    assert week.cycle_week == 3
    assert aioclient_mock.call_count == 1
    _, url, _, headers = aioclient_mock.mock_calls[0]
    assert url.query["date"] == "26-10-2026"
    assert "ha-wdc-school-meals" in headers["User-Agent"]


async def test_fetch_week_outside_the_year(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        f"{Menu.PRIMARY.url}?date=05-07-2027",
        text=load_page("primary-menus-05-07-2027.html"),
    )
    client = WdcClient(async_get_clientsession(hass))

    assert await client.fetch_week(Menu.PRIMARY, date(2027, 7, 7)) is None


@pytest.mark.parametrize(
    "mock",
    [{"status": 500}, {"exc": ClientError()}, {"exc": TimeoutError()}],
)
async def test_fetch_week_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock: dict
) -> None:
    aioclient_mock.get(Menu.PRIMARY.url, **mock)
    client = WdcClient(async_get_clientsession(hass))

    with pytest.raises(WdcConnectionError):
        await client.fetch_week(Menu.PRIMARY, date(2026, 10, 28))
