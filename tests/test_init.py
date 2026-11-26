"""Setting up, sharing fetchers, unloading and failing."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.const import DOMAIN, TITLE
from custom_components.wdc_school_meals.models import BASE_URL, Menu
from custom_components.wdc_school_meals.terms import TERM_DATES_PATH

from .conftest import child, main_entry, setup_entry
from .pages import load_page

NOW = "2026-10-28 10:00:00+00:00"


async def test_setup_and_unload_without_children(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title=TITLE)
    await setup_entry(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_children_on_one_menu_share_a_fetch(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to(NOW)
    entry = main_entry(
        [
            child(Menu.PRIMARY, "balloch-primary-school", "Alex"),
            child(Menu.PRIMARY, "renton-primary-school", "Jordan"),
            child(Menu.SECONDARY, "dumbarton-academy", "Taylor"),
        ]
    )
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert set(entry.runtime_data.coordinators) == {Menu.PRIMARY, Menu.SECONDARY}
    menu_calls = [
        str(url) for _, url, _, _ in mock_wdc.mock_calls if "date=" in str(url)
    ]
    # This week and next, once per menu
    assert len(menu_calls) == 4

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert sorted(d.name for d in devices) == [
        "Alex's School Meals",
        "Jordan's School Meals",
        "Taylor's School Meals",
    ]
    alex = next(d for d in devices if d.name == "Alex's School Meals")
    assert alex.model == "Primary menu"
    assert alex.manufacturer == "West Dunbartonshire Council"
    assert alex.entry_type is dr.DeviceEntryType.SERVICE


async def test_site_down_retries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to(NOW)
    aioclient_mock.get(f"{BASE_URL}{TERM_DATES_PATH}", status=503)
    aioclient_mock.get(Menu.PRIMARY.url, status=503)
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school")])
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_changed_menu_page_raises_a_repair(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to(NOW)
    aioclient_mock.get(f"{BASE_URL}{TERM_DATES_PATH}", status=503)
    aioclient_mock.get(Menu.PRIMARY.url, text="<html><body>New look!</body></html>")
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school")])
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "menu_layout_changed_primary")
    assert issue is not None
    assert issue.translation_placeholders == {
        "menu": "Primary",
        "url": Menu.PRIMARY.url,
    }


async def test_unreadable_term_dates_raise_a_repair(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-13 10:00:00+01:00")  # a Tuesday in the October break
    aioclient_mock.get(f"{BASE_URL}{TERM_DATES_PATH}", text="<p>Coming soon</p>")
    # Any menu page will do: this test is about the term dates
    aioclient_mock.get(
        Menu.PRIMARY.url, text=load_page("primary-menus-26-10-2026.html")
    )
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school")])
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(DOMAIN, "term_dates_unreadable")
    # Without term dates a holiday weekday counts as a school day
    snapshot = entry.runtime_data.coordinators[Menu.PRIMARY].data
    assert snapshot.today_closure is None
    assert snapshot.terms_known is False


async def test_adding_a_child_reloads(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to(NOW)
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    await setup_entry(hass, entry)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "child"), context={"source": "user"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "school"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"school": "dumbarton-academy", "name": "Taylor"}
    )
    await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert set(entry.runtime_data.coordinators) == {Menu.PRIMARY, Menu.SECONDARY}
    assert len(entry.subentries) == 2
