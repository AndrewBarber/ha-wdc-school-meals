"""Turn a day's menu into short text for states and calendar events.

Primary, nursery and Kilpatrick Primary list "Meal 1" and "Meal 2", each a main
followed by its sides, so the choice is the first dish of each. Secondary and
Kilpatrick High list every main under "Main Courses".
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .models import Course, Day, Dish

MAX_STATE = 255
MEAL_RE = re.compile(r"^meal\s+\d+$", re.I)
MAINS_RE = re.compile(r"^main\s+courses?$", re.I)


def main_choices(day: Day) -> list[str]:
    """The mains to choose between, in page order."""
    choices: list[str] = []
    for course in day.courses:
        if not course.dishes:
            continue
        if MEAL_RE.match(course.name):
            choices.append(course.dishes[0].name)
        elif MAINS_RE.match(course.name):
            choices.extend(dish.name for dish in course.dishes)
    if not choices:
        first = next((c for c in day.courses if c.dishes), None)
        if first:
            choices.append(first.dishes[0].name)
    return list(dict.fromkeys(choices))


def summary(day: Day) -> str:
    """ "Vegetable Curry or Macaroni Cheese", cut to fit a state."""
    text = " or ".join(main_choices(day))
    return text if len(text) <= MAX_STATE else text[: MAX_STATE - 3].rstrip() + "..."


NOT_CHECKED = "allergens not checked"


def describe(
    day: Day,
    allergens: Mapping[str, tuple[str, ...]] | None = None,
    mark_unchecked: bool = False,
) -> str:
    """Every course on its own line, for a calendar event.

    With allergens (dish URL to names), each dish that has any gets them in
    brackets: "Macaroni Cheese (Gluten, Wheat, Milk)". With mark_unchecked, a
    dish the council flags as containing allergens whose page has not been
    read says so, rather than looking allergen free.
    """
    allergens = allergens or {}

    def dish_text(dish: Dish) -> str:
        found = allergens.get(dish.url) if dish.url else None
        if found:
            return f"{dish.name} ({', '.join(found)})"
        if mark_unchecked and dish.contains_allergens and found is None:
            return f"{dish.name} ({NOT_CHECKED})"
        return dish.name

    return "\n".join(
        f"{course.name}: " + ", ".join(dish_text(dish) for dish in course.dishes)
        for course in day.courses
        if course.dishes
    )


def course_text(course: Course) -> str:
    """ "Fresh Bread, Fresh Fruit Platter, Oatie Biscuits", cut to fit a state."""
    text = ", ".join(dish.name for dish in course.dishes)
    return text if len(text) <= MAX_STATE else text[: MAX_STATE - 3].rstrip() + "..."


def course_attributes(
    course: Course, allergens: Mapping[str, tuple[str, ...]] | None = None
) -> dict[str, Any]:
    """Flags for one course, plus named allergens when known."""
    attrs: dict[str, Any] = {
        "dishes": [dish.name for dish in course.dishes],
        "vegetarian": [d.name for d in course.dishes if d.vegetarian],
        "contains_allergens": [d.name for d in course.dishes if d.contains_allergens],
    }
    if allergens:
        attrs["allergens"] = {
            dish.name: list(found)
            for dish in course.dishes
            if dish.url and (found := allergens.get(dish.url))
        }
    return attrs


def attributes(
    day: Day, allergens: Mapping[str, tuple[str, ...]] | None = None
) -> dict[str, Any]:
    """Courses and flags, small enough for state attributes.

    With allergens (dish URL to names), adds "allergens": dish name to its
    named allergens, for dishes that have any.
    """
    dishes = [dish for course in day.courses for dish in course.dishes]
    extra: dict[str, Any] = {}
    if allergens:
        extra["allergens"] = {
            dish.name: list(found)
            for dish in dishes
            if dish.url and (found := allergens.get(dish.url))
        }
    return {
        "courses": {
            course.name: [dish.name for dish in course.dishes] for course in day.courses
        },
        "vegetarian": list(dict.fromkeys(d.name for d in dishes if d.vegetarian)),
        "contains_allergens": list(
            dict.fromkeys(d.name for d in dishes if d.contains_allergens)
        ),
        **extra,
    }
