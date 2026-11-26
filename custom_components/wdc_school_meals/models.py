"""Plain data types for the menus. No Home Assistant imports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

BASE_URL = "https://www.west-dunbarton.gov.uk"
SCHOOL_MEALS_PATH = "/schools-and-learning/schools/school-meals"


class Menu(StrEnum):
    """The five menus the council publishes."""

    NURSERY = "nursery"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    KILPATRICK_PRIMARY = "kilpatrick_primary"
    KILPATRICK_HIGH = "kilpatrick_high"

    @property
    def path(self) -> str:
        """Page path on the council site."""
        return f"{SCHOOL_MEALS_PATH}/{MENU_SLUGS[self]}"

    @property
    def url(self) -> str:
        """Full URL of the menu page."""
        return f"{BASE_URL}{self.path}"

    @property
    def label(self) -> str:
        """Name as the council writes it."""
        return MENU_LABELS[self]


MENU_SLUGS: dict[Menu, str] = {
    Menu.NURSERY: "nursery-menus",
    Menu.PRIMARY: "primary-menus",
    Menu.SECONDARY: "secondary-menus",
    Menu.KILPATRICK_PRIMARY: "kilpatrick-primary-school",
    Menu.KILPATRICK_HIGH: "kilpatrick-high-school",
}

MENU_LABELS: dict[Menu, str] = {
    Menu.NURSERY: "Nursery",
    Menu.PRIMARY: "Primary",
    Menu.SECONDARY: "Secondary",
    Menu.KILPATRICK_PRIMARY: "Kilpatrick Primary",
    Menu.KILPATRICK_HIGH: "Kilpatrick High",
}


# The rows each menu's day table has, as keys made by course_key(). One course
# sensor per row; a row the council adds later still shows in attributes.
_SCHOOL_PRIMARY = ("starter_dessert", "meal_1", "meal_2", "drinks")
_SCHOOL_SECONDARY = (
    "starter_dessert",
    "main_courses",
    "sides",
    "vegetables",
    "grab_and_go",
    "snacks",
)
MENU_COURSES: dict[Menu, tuple[str, ...]] = {
    Menu.NURSERY: (*_SCHOOL_PRIMARY, "snack_am", "snack_pm"),
    Menu.PRIMARY: _SCHOOL_PRIMARY,
    Menu.SECONDARY: _SCHOOL_SECONDARY,
    Menu.KILPATRICK_PRIMARY: _SCHOOL_PRIMARY,
    Menu.KILPATRICK_HIGH: _SCHOOL_SECONDARY,
}


def course_key(name: str) -> str:
    """ "Starter/Dessert" to "starter_dessert", "Meal 1" to "meal_1"."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


@dataclass(frozen=True, slots=True)
class Dish:
    """One item on a day's menu."""

    name: str
    url: str | None = None
    vegetarian: bool = False
    contains_allergens: bool = False


@dataclass(frozen=True, slots=True)
class Course:
    """A row of the day table, e.g. "Meal 1" or "Main Courses"."""

    name: str
    dishes: tuple[Dish, ...]


@dataclass(frozen=True, slots=True)
class Day:
    """What is served on one date."""

    date: date
    courses: tuple[Course, ...]

    def course(self, name: str) -> Course | None:
        """The course with this name, if any."""
        return next((c for c in self.courses if c.name == name), None)

    def course_by_key(self, key: str) -> Course | None:
        """The course whose course_key() is key, if any."""
        return next((c for c in self.courses if course_key(c.name) == key), None)


@dataclass(frozen=True, slots=True)
class Week:
    """One menu week as the council page shows it."""

    menu: Menu
    monday: date
    label: str | None
    cycle_week: int | None
    days: tuple[Day, ...]

    def day(self, on: date) -> Day | None:
        """The menu for a date in this week, if there is one."""
        return next((d for d in self.days if d.date == on), None)
