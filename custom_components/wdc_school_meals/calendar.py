"""A lunch calendar per child: one all day event per school day."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import WdcSchoolMealsConfigEntry
from .api import WdcConnectionError
from .const import CONF_WEEKS_AHEAD, DEFAULT_WEEKS_AHEAD, WEEKS_BACK
from .coordinator import DishCache
from .dates import monday_of
from .entity import WdcEntity
from .models import Day
from .parser import ParseError
from .summary import describe, summary

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WdcSchoolMealsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """One calendar per child."""
    for subentry, coordinator in entry.runtime_data.children(entry):
        async_add_entities(
            [LunchCalendar(coordinator, subentry, "lunches", "calendar")],
            config_subentry_id=subentry.subentry_id,
        )


def _event(day: Day, dishes: DishCache | None = None) -> CalendarEvent:
    # Dish pages are only read for today and the next school day, so with
    # allergens on, other days mark flagged dishes as not checked.
    allergens = {}
    if dishes is not None:
        allergens = {
            dish.url: details.allergens
            for course in day.courses
            for dish in course.dishes
            if (details := dishes.get(dish.url))
        }
    return CalendarEvent(
        start=day.date,
        end=day.date + timedelta(days=1),
        summary=summary(day),
        description=describe(day, allergens, mark_unchecked=dishes is not None),
    )


class LunchCalendar(WdcEntity, CalendarEntity):
    """School lunches, skipping weekends, holidays and in-service days."""

    @property
    def event(self) -> CalendarEvent | None:
        """Today's lunch, or the next school day's."""
        data = self.coordinator.data
        dishes = self.coordinator.dishes
        if data.today_menu:
            return _event(data.today_menu, dishes)
        return _event(data.next_menu, dishes) if data.next_menu else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Lunches in a range, fetching weeks the cache does not have."""
        entry = self.coordinator.config_entry
        weeks_ahead = int(entry.options.get(CONF_WEEKS_AHEAD, DEFAULT_WEEKS_AHEAD))
        this_monday = monday_of(dt_util.now().date())
        first = max(
            dt_util.as_local(start_date).date(),
            this_monday - timedelta(weeks=WEEKS_BACK),
        )
        # end_date is exclusive; an all day event on the end day does not overlap.
        last = min(
            (dt_util.as_local(end_date) - timedelta(microseconds=1)).date(),
            this_monday + timedelta(weeks=weeks_ahead, days=6),
        )
        calendar = self.coordinator.terms.calendar
        events: list[CalendarEvent] = []
        day = first
        while day <= last:
            if calendar.is_school_day(day):
                try:
                    week = await self.coordinator.async_get_week(day)
                except (WdcConnectionError, ParseError) as err:
                    _LOGGER.warning("No lunches for the week of %s: %s", day, err)
                    day = monday_of(day) + timedelta(days=7)
                    continue
                menu = week.day(day) if week else None
                if menu:
                    events.append(_event(menu, self.coordinator.dishes))
            day += timedelta(days=1)
        return events
