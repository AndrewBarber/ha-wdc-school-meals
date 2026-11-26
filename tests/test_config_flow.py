"""Config flow: the main entry, its options, and the child subentries."""

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wdc_school_meals.const import (
    CONF_ALLERGENS,
    CONF_MENU,
    CONF_SCHOOL,
    CONF_WATCH,
    CONF_WEEKS_AHEAD,
    DOMAIN,
    SUBENTRY_CHILD,
    TITLE,
)
from custom_components.wdc_school_meals.models import Menu

from .conftest import child, main_entry


async def test_user_step_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == {}


async def test_second_entry_is_refused(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, title=TITLE).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options(hass: HomeAssistant) -> None:
    entry = main_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_WEEKS_AHEAD: 3.0}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_WEEKS_AHEAD: 3, CONF_ALLERGENS: False}


async def _start_child(hass: HomeAssistant, entry: MockConfigEntry, path: str):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_CHILD), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": path}
    )


async def _allergies(hass: HomeAssistant, result, watch: list[str] | None = None):
    """Answer the last step, which asks for allergens to watch."""
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "allergies"
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_WATCH: watch} if watch is not None else {}
    )


async def test_add_child_by_school(hass: HomeAssistant) -> None:
    entry = main_entry()
    entry.add_to_hass(hass)

    result = await _start_child(hass, entry, "school")
    assert result["step_id"] == "school"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_SCHOOL: "balloch-primary-school", CONF_NAME: " Alex "},
    )
    result = await _allergies(hass, result)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Alex's School Meals"
    (subentry,) = entry.subentries.values()
    assert dict(subentry.data) == {
        CONF_NAME: "Alex",
        CONF_SCHOOL: "balloch-primary-school",
        CONF_MENU: "primary",
        CONF_WATCH: [],
    }
    assert subentry.unique_id == "balloch-primary-school:alex"


async def test_add_child_with_allergens_to_watch(hass: HomeAssistant) -> None:
    entry = main_entry()
    entry.add_to_hass(hass)

    result = await _start_child(hass, entry, "school")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SCHOOL: "balloch-primary-school", CONF_NAME: "Alex"}
    )
    result = await _allergies(hass, result, ["milk", "eggs"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    (subentry,) = entry.subentries.values()
    assert subentry.data[CONF_WATCH] == ["milk", "eggs"]


async def test_add_child_without_a_name(hass: HomeAssistant) -> None:
    entry = main_entry()
    entry.add_to_hass(hass)

    result = await _start_child(hass, entry, "school")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SCHOOL: "dumbarton-academy"}
    )
    result = await _allergies(hass, result)

    assert result["title"] == "Dumbarton Academy Meals"
    (subentry,) = entry.subentries.values()
    assert subentry.data[CONF_MENU] == "secondary"
    assert subentry.data[CONF_NAME] is None


async def test_school_with_two_menus_asks_which(hass: HomeAssistant) -> None:
    entry = main_entry()
    entry.add_to_hass(hass)

    result = await _start_child(hass, entry, "school")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SCHOOL: "kilpatrick-schools", CONF_NAME: "Taylor"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "stage"
    assert result["description_placeholders"] == {"school": "Kilpatrick Schools"}

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_MENU: "kilpatrick_high"}
    )
    result = await _allergies(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    (subentry,) = entry.subentries.values()
    assert subentry.data[CONF_MENU] == "kilpatrick_high"


async def test_add_child_by_menu(hass: HomeAssistant) -> None:
    entry = main_entry()
    entry.add_to_hass(hass)

    result = await _start_child(hass, entry, "menu")
    assert result["step_id"] == "menu"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_MENU: "nursery"}
    )
    result = await _allergies(hass, result)

    assert result["title"] == "Nursery School Meals"
    (subentry,) = entry.subentries.values()
    assert subentry.data[CONF_SCHOOL] is None
    assert subentry.unique_id == "nursery:"


async def test_same_child_twice_is_refused(hass: HomeAssistant) -> None:
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    entry.add_to_hass(hass)

    result = await _start_child(hass, entry, "school")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_SCHOOL: "balloch-primary-school", CONF_NAME: "alex"},
    )
    result = await _allergies(hass, result)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_two_children_at_one_school(hass: HomeAssistant) -> None:
    entry = main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex")])
    entry.add_to_hass(hass)

    result = await _start_child(hass, entry, "school")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SCHOOL: "balloch-primary-school", CONF_NAME: "Jordan"}
    )
    result = await _allergies(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(entry.subentries) == 2


async def _start_reconfigure(hass: HomeAssistant, entry: MockConfigEntry, path: str):
    (subentry,) = entry.subentries.values()
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_CHILD),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry.subentry_id},
    )
    assert result["type"] is FlowResultType.MENU
    return subentry.subentry_id, await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": path}
    )


async def test_reconfigure_moves_up_to_high_school(hass: HomeAssistant) -> None:
    entry = main_entry(
        [child(Menu.PRIMARY, "balloch-primary-school", "Alex", ["milk"])]
    )
    entry.add_to_hass(hass)

    subentry_id, result = await _start_reconfigure(hass, entry, "school")
    assert result["step_id"] == "school"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_SCHOOL: "vale-of-leven-academy", CONF_NAME: "Alex"},
    )
    # The watch list is kept as the default
    schema = result["data_schema"].schema
    (field,) = schema
    assert field.default() == ["milk"]
    result = await _allergies(hass, result, ["milk"])

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    subentry = entry.subentries[subentry_id]
    assert subentry.title == "Alex's School Meals"
    assert subentry.data[CONF_MENU] == "secondary"
    assert subentry.data[CONF_WATCH] == ["milk"]
    assert subentry.unique_id == "vale-of-leven-academy:alex"


async def test_reconfigure_by_menu_keeps_the_name(hass: HomeAssistant) -> None:
    entry = main_entry([child(Menu.NURSERY, None, "Robin")])
    entry.add_to_hass(hass)

    subentry_id, result = await _start_reconfigure(hass, entry, "menu")
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_MENU: "primary", CONF_NAME: "Robin"}
    )
    result = await _allergies(hass, result)

    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[subentry_id].data[CONF_MENU] == "primary"
