"""Is school open today, and does a menu list a child's watched allergen."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WdcSchoolMealsConfigEntry
from .allergens import Allergen, DayCheck, check_day
from .const import CONF_WATCH
from .coordinator import MenuCoordinator
from .entity import WdcEntity
from .models import Day

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WdcSchoolMealsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """School day per child, plus two allergen sensors if they watch any."""
    for subentry, coordinator in entry.runtime_data.children(entry):
        entities: list[BinarySensorEntity] = [
            SchoolDaySensor(coordinator, subentry, "school_day", "binary_sensor")
        ]
        if subentry.data.get(CONF_WATCH):
            entities += [
                WatchedAllergenSensor(coordinator, subentry, key, "binary_sensor")
                for key in (
                    "watched_allergen_today",
                    "watched_allergen_next_school_day",
                )
            ]
        async_add_entities(entities, config_subentry_id=subentry.subentry_id)


class SchoolDaySensor(WdcEntity, BinarySensorEntity):
    """On when pupils are in today."""

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.today_closure is None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        next_closure = data.next_closure
        return {
            "closure_reason": data.today_closure,
            "next_school_day": data.next_date.isoformat() if data.next_date else None,
            "next_closure": next_closure[0].isoformat() if next_closure else None,
            "next_closure_reason": next_closure[1] if next_closure else None,
            "term_dates_known": data.terms_known,
        }


class WatchedAllergenSensor(WdcEntity, BinarySensorEntity):
    """On when a dish that day lists one of the child's watched allergens.

    Unknown (not off) when nothing matches but a dish flagged as containing
    allergens has no named allergens to check. Only what the council
    publishes, with "may contain" warnings on some dishes only, so off never
    means safe.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: MenuCoordinator,
        subentry: ConfigSubentry,
        key: str,
        domain: str,
    ) -> None:
        super().__init__(coordinator, subentry, key, domain)
        self._watch = [Allergen(a) for a in subentry.data[CONF_WATCH]]
        self._next = key == "watched_allergen_next_school_day"

    def _day(self) -> tuple[date | None, Day | None]:
        data = self.coordinator.data
        if self._next:
            return data.next_date, data.next_menu
        return data.today, data.today_menu

    def _check(self) -> DayCheck | None:
        _, menu = self._day()
        if menu is None:
            return None
        allergens = self.coordinator.data.allergens
        return check_day(menu, self._watch, allergens.get)

    @property
    def is_on(self) -> bool | None:
        check = self._check()
        if check is None:
            # No lunch: closed today is a clear "no"; a missing menu is unknown
            return (
                False
                if not self._next and self.coordinator.data.today_closure
                else None
            )
        return check.alert

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        day, _ = self._day()
        check = self._check()
        return {
            "date": day.isoformat() if day else None,
            "watching": [a.value for a in self._watch],
            "contains": check.contains if check else {},
            "unknown": check.unknown if check else [],
        }
