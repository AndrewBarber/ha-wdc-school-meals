"""West Dunbartonshire School Meals.

Unofficial. Reads the school meal menus West Dunbartonshire Council publishes
on its website. One main config entry; each child is a subentry with its own
device. Children on the same menu share one coordinator.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .api import WdcClient
from .const import CONF_ALLERGENS, CONF_MENU, CONF_WATCH, DOMAIN, SUBENTRY_CHILD
from .coordinator import (
    DISH_STORE_KEY,
    DISH_STORE_VERSION,
    DishCache,
    MenuCoordinator,
    TermDates,
)
from .entity import child_device_info
from .models import Menu
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


@dataclass
class WdcRuntimeData:
    """Shared by every child of the entry."""

    client: WdcClient
    terms: TermDates
    coordinators: dict[Menu, MenuCoordinator]
    dishes: DishCache | None = None

    def children(
        self, entry: WdcSchoolMealsConfigEntry
    ) -> list[tuple[ConfigSubentry, MenuCoordinator]]:
        """Each child subentry with the coordinator for its menu."""
        return [
            (subentry, self.coordinators[Menu(subentry.data[CONF_MENU])])
            for subentry in entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_CHILD
        ]


type WdcSchoolMealsConfigEntry = ConfigEntry[WdcRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the get_menu action."""
    async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: WdcSchoolMealsConfigEntry
) -> bool:
    """Set up the shared fetchers, then the children's entities."""
    client = WdcClient(async_get_clientsession(hass))
    terms = TermDates(hass, client)
    dishes: DishCache | None = None
    # Dish pages are read for named allergens, or when any child watches one.
    if entry.options.get(CONF_ALLERGENS) or any(
        subentry.data.get(CONF_WATCH) for subentry in entry.subentries.values()
    ):
        dishes = DishCache(hass, client)
        await dishes.async_load()
    menus = {
        Menu(subentry.data[CONF_MENU])
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_CHILD
    }
    coordinators = {
        menu: MenuCoordinator(hass, entry, client, terms, menu, dishes)
        for menu in sorted(menus)
    }
    await asyncio.gather(
        *(c.async_config_entry_first_refresh() for c in coordinators.values())
    )
    entry.runtime_data = WdcRuntimeData(client, terms, coordinators, dishes)

    device_registry = dr.async_get(hass)
    for subentry, coordinator in entry.runtime_data.children(entry):
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            **child_device_info(subentry, coordinator.menu),
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: WdcSchoolMealsConfigEntry) -> None:
    """Children added, changed or removed, or options changed."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: WdcSchoolMealsConfigEntry
) -> bool:
    """Unload the config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant, entry: WdcSchoolMealsConfigEntry
) -> None:
    """Delete the saved dish pages along with the integration."""
    await Store(hass, DISH_STORE_VERSION, DISH_STORE_KEY).async_remove()
