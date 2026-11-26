"""The get_menu action: a child's lunch on any date, as response data."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DATE, ATTR_ENTITY_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .api import WdcConnectionError
from .const import CONF_MENU, DOMAIN
from .models import Menu
from .parser import ParseError
from .summary import attributes, summary

SERVICE_GET_MENU = "get_menu"

GET_MENU_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_DATE): cv.date,
    }
)


async def _get_menu(call: ServiceCall) -> ServiceResponse:
    hass = call.hass
    entity_id: str = call.data[ATTR_ENTITY_ID]
    day: date = call.data.get(ATTR_DATE) or dt_util.now().date()

    entity = er.async_get(hass).async_get(entity_id)
    if (
        entity is None
        or entity.platform != DOMAIN
        or entity.config_entry_id is None
        or entity.config_subentry_id is None
    ):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_a_child_entity",
            translation_placeholders={"entity_id": entity_id},
        )
    entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="not_loaded"
        )
    subentry = entry.subentries[entity.config_subentry_id]
    runtime = entry.runtime_data
    coordinator = runtime.coordinators[Menu(subentry.data[CONF_MENU])]

    closure = runtime.terms.calendar.closure_reason(day)
    try:
        week = await coordinator.async_get_week(day)
    except (WdcConnectionError, ParseError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="menu_unavailable",
            translation_placeholders={"menu": coordinator.menu.label},
        ) from err
    menu = week.day(day) if week and closure is None else None

    allergens: dict[str, tuple[str, ...]] = {}
    if menu and runtime.dishes is not None:
        urls = [d.url for c in menu.courses for d in c.dishes if d.url]
        await runtime.dishes.async_fetch(urls)
        allergens = {
            url: details.allergens
            for url in urls
            if (details := runtime.dishes.get(url))
        }

    response: dict[str, Any] = {
        "date": day.isoformat(),
        "child": subentry.title,
        "menu": coordinator.menu.label,
        "school_day": closure is None,
        "closure_reason": closure,
        "cycle_week": week.cycle_week if week else None,
        "summary": summary(menu) if menu else None,
    }
    if menu:
        response.update(attributes(menu, allergens))
    return response


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions once, whatever entries exist."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_MENU,
        _get_menu,
        schema=GET_MENU_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
