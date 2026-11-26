"""Shared pytest setup. pytest-homeassistant-custom-component provides hass."""

import re
from collections.abc import Iterable
from typing import Any

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.config_flow import (
    child_title,
    child_unique_id,
)
from custom_components.wdc_school_meals.const import (
    CONF_MENU,
    CONF_SCHOOL,
    CONF_WATCH,
    DOMAIN,
    SUBENTRY_CHILD,
    TITLE,
)
from custom_components.wdc_school_meals.models import BASE_URL, MENU_SLUGS, Menu
from custom_components.wdc_school_meals.terms import TERM_DATES_PATH

from .pages import load_page

# Mondays saved by scripts/refresh-fixtures, per menu
SAVED_WEEKS: dict[Menu, tuple[str, ...]] = {
    Menu.PRIMARY: (
        "26-10-2026",
        "02-11-2026",
        "09-11-2026",
        "16-11-2026",
        "28-12-2026",
        "04-01-2027",
        "05-07-2027",
    ),
    Menu.SECONDARY: ("26-10-2026", "02-11-2026"),
    Menu.NURSERY: ("26-10-2026",),
    Menu.KILPATRICK_PRIMARY: ("26-10-2026",),
    Menu.KILPATRICK_HIGH: ("26-10-2026",),
}
TERM_PAGES = ("term-date-202627", "term-dates-202728")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let HA load integrations from custom_components/ in every test."""
    return


@pytest.fixture(autouse=True)
async def london(hass: HomeAssistant) -> None:
    """Days roll over at midnight UK time."""
    await hass.config.async_set_time_zone("Europe/London")


@pytest.fixture
def mock_wdc(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Answer every request with a saved council page."""
    for menu, mondays in SAVED_WEEKS.items():
        for monday in mondays:
            aioclient_mock.get(
                f"{menu.url}?date={monday}",
                text=load_page(f"{MENU_SLUGS[menu]}-{monday}.html"),
            )
    for page in TERM_PAGES:
        aioclient_mock.get(
            f"{BASE_URL}{TERM_DATES_PATH}/{page}", text=load_page(f"{page}.html")
        )
    aioclient_mock.get(
        f"{BASE_URL}{TERM_DATES_PATH}", text=load_page("term-dates.html")
    )
    return aioclient_mock


def child(
    menu: Menu,
    school: str | None = None,
    name: str | None = None,
    watch: list[str] | None = None,
) -> ConfigSubentryData:
    """A child subentry as the flow would create it."""
    return ConfigSubentryData(
        data={
            CONF_NAME: name,
            CONF_SCHOOL: school,
            CONF_MENU: menu.value,
            CONF_WATCH: watch or [],
        },
        subentry_type=SUBENTRY_CHILD,
        title=child_title(name, school, menu),
        unique_id=child_unique_id(name, school, menu),
    )


def main_entry(
    children: Iterable[ConfigSubentryData] = (), options: dict[str, Any] | None = None
) -> MockConfigEntry:
    """The main entry with its children."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        options=options or {},
        subentries_data=list(children),
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up an entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


MEALS = f"{BASE_URL}/schools-and-learning/schools/school-meals/meals"


@pytest.fixture
def mock_dishes(mock_wdc: AiohttpClientMocker) -> AiohttpClientMocker:
    """Two real dish pages; every other dish has no allergens (peas)."""
    for dish in ("main/macaroni-cheese", "main/beef-burger-in-a-bun-with-cheese"):
        mock_wdc.get(
            f"{MEALS}/{dish}", text=load_page(f"dish-{dish.replace('/', '-')}.html")
        )
    mock_wdc.get(
        re.compile(re.escape(MEALS) + "/.*"),
        text=load_page("dish-side-dish-peas.html"),
    )
    return mock_wdc
