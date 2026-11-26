"""Today's lunch, the next school day's lunch, and the cycle week."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WdcSchoolMealsConfigEntry
from .entity import WdcEntity
from .models import MENU_COURSES, Day
from .summary import attributes, course_attributes, course_text, summary

PARALLEL_UPDATES = 0

NO_SCHOOL = "No school"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WdcSchoolMealsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Three sensors per child."""
    for subentry, coordinator in entry.runtime_data.children(entry):
        async_add_entities(
            [
                TodaySensor(coordinator, subentry, "today", "sensor"),
                NextSchoolDaySensor(coordinator, subentry, "next_school_day", "sensor"),
                CycleWeekSensor(coordinator, subentry, "cycle_week", "sensor"),
                *(
                    CourseSensor(coordinator, subentry, f"{day}_{course}", "sensor")
                    for day in ("today", "next_school_day")
                    for course in MENU_COURSES[coordinator.menu]
                ),
            ],
            config_subentry_id=subentry.subentry_id,
        )


def _menu_attributes(
    day: date | None, menu: Day | None, allergens: Mapping[str, tuple[str, ...]]
) -> dict[str, Any]:
    attrs: dict[str, Any] = {"date": day.isoformat() if day else None}
    if menu:
        attrs.update(attributes(menu, allergens))
    return attrs


class TodaySensor(WdcEntity, SensorEntity):
    """The main choices today, or "No school"."""

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if data.today_closure:
            return NO_SCHOOL
        return summary(data.today_menu) if data.today_menu else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            **_menu_attributes(data.today, data.today_menu, data.allergens),
            "cycle_week": data.cycle_week,
            "closure_reason": data.today_closure,
            "menu_url": self.coordinator.menu.url,
        }


class NextSchoolDaySensor(WdcEntity, SensorEntity):
    """The main choices on the next school day (Friday shows Monday)."""

    @property
    def native_value(self) -> str | None:
        menu = self.coordinator.data.next_menu
        return summary(menu) if menu else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            **_menu_attributes(data.next_date, data.next_menu, data.allergens),
            "menu_url": self.coordinator.menu.url,
        }


class CycleWeekSensor(WdcEntity, SensorEntity):
    """Week 1, 2 or 3 of the council's three week cycle."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.cycle_week


class CourseSensor(WdcEntity, SensorEntity):
    """One course (e.g. Starter/Dessert) today or on the next school day."""

    @property
    def _next(self) -> bool:
        return self._attr_translation_key.startswith("next_school_day_")

    @property
    def _course(self) -> str:
        key = self._attr_translation_key
        return key.removeprefix("next_school_day_").removeprefix("today_")

    def _day(self) -> tuple[date | None, Day | None]:
        data = self.coordinator.data
        if self._next:
            return data.next_date, data.next_menu
        return data.today, data.today_menu

    @property
    def native_value(self) -> str | None:
        if not self._next and self.coordinator.data.today_closure:
            return NO_SCHOOL
        _, menu = self._day()
        course = menu.course_by_key(self._course) if menu else None
        return course_text(course) if course and course.dishes else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        day, menu = self._day()
        attrs: dict[str, Any] = {"date": day.isoformat() if day else None}
        course = menu.course_by_key(self._course) if menu else None
        if course:
            attrs["course"] = course.name
            attrs.update(course_attributes(course, self.coordinator.data.allergens))
        return attrs
