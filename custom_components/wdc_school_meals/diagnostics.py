"""Diagnostics download: children, cached weeks and term dates."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import WdcSchoolMealsConfigEntry
from .const import CONF_WATCH

# Which allergens a child watches is health information.
TO_REDACT = {CONF_WATCH}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: WdcSchoolMealsConfigEntry
) -> dict[str, Any]:
    """Children's names and schools; their watched allergens are redacted."""
    runtime = entry.runtime_data
    calendar = runtime.terms.calendar
    return {
        "options": dict(entry.options),
        "dishes_cached": len(runtime.dishes) if runtime.dishes is not None else None,
        "children": [
            {
                "title": subentry.title,
                "data": async_redact_data(subentry.data, TO_REDACT),
            }
            for subentry, _ in runtime.children(entry)
        ],
        "menus": {
            menu.value: {
                "last_update_success": coordinator.last_update_success,
                "today": coordinator.data.today.isoformat(),
                "today_closure": coordinator.data.today_closure,
                "next_date": (
                    coordinator.data.next_date.isoformat()
                    if coordinator.data.next_date
                    else None
                ),
                "cycle_week": coordinator.data.cycle_week,
                "weeks": {
                    monday.isoformat(): (
                        {"label": week.label, "days": len(week.days)} if week else None
                    )
                    for monday, week in coordinator.data.weeks.items()
                },
            }
            for menu, coordinator in runtime.coordinators.items()
        },
        "term_dates": [
            {
                "first_day": year.first_day.isoformat(),
                "last_day": year.last_day.isoformat(),
                "closures": len(year.closures),
            }
            for year in calendar.years
        ],
    }
