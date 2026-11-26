"""Base entity: one device per child, named after the child or school."""

from __future__ import annotations

import re

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import MenuCoordinator
from .models import Menu

POSSESSIVE_RE = re.compile(r"['\u2019]s\b")


def object_id_base(title: str) -> str:
    """ "Alex's School Meals" to "alex_school_meals", not "alexs_school_meals"."""
    return slugify(POSSESSIVE_RE.sub("", title))


def child_device_info(subentry: ConfigSubentry, menu: Menu) -> DeviceInfo:
    """The child's device, shared by setup and every entity."""
    return DeviceInfo(
        identifiers={(DOMAIN, subentry.subentry_id)},
        name=subentry.title,
        manufacturer=MANUFACTURER,
        model=f"{menu.label} menu",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=menu.url,
    )


class WdcEntity(CoordinatorEntity[MenuCoordinator]):
    """An entity on a child's device."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: MenuCoordinator,
        subentry: ConfigSubentry,
        key: str,
        domain: str,
    ) -> None:
        super().__init__(coordinator)
        self._subentry = subentry
        self._attr_translation_key = key
        self._attr_unique_id = f"{subentry.subentry_id}_{key}"
        self.entity_id = f"{domain}.{object_id_base(subentry.title)}_{key}"
        self._attr_device_info = child_device_info(subentry, coordinator.menu)
