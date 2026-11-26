"""Constants for West Dunbartonshire School Meals."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "wdc_school_meals"
TITLE: Final = "West Dunbartonshire School Meals"
MANUFACTURER: Final = "West Dunbartonshire Council"
ATTRIBUTION: Final = (
    "Menus from West Dunbartonshire Council. Unofficial: always check menus "
    "and allergens with the school."
)

SUBENTRY_CHILD: Final = "child"
CONF_SCHOOL: Final = "school"
CONF_MENU: Final = "menu"
CONF_WEEKS_AHEAD: Final = "weeks_ahead"
DEFAULT_WEEKS_AHEAD: Final = 2
CONF_ALLERGENS: Final = "allergens"
CONF_WATCH: Final = "watch_allergens"

UPDATE_INTERVAL: Final = timedelta(hours=6)
# Menus are set for the year and same-day swaps are not published, so a
# fetched week is good for half a day. Refreshes reuse it.
WEEK_MAX_AGE: Final = timedelta(hours=12)
# How far back the calendar shows (a month view), and so how far back cached
# weeks are kept.
WEEKS_BACK: Final = 5
TERMS_MAX_AGE: Final = timedelta(hours=24)
DISH_MAX_AGE: Final = timedelta(days=7)
