"""State and event text from a day's menu."""

from datetime import date

from custom_components.wdc_school_meals.models import Course, Day, Dish
from custom_components.wdc_school_meals.summary import (
    MAX_STATE,
    describe,
    main_choices,
    summary,
)

DAY = date(2026, 10, 28)


def _day(*courses: tuple[str, list[str]]) -> Day:
    return Day(
        DAY,
        tuple(Course(name, tuple(Dish(d) for d in dishes)) for name, dishes in courses),
    )


def test_meal_rows_give_their_first_dish() -> None:
    day = _day(("Meal 1", ["Curry", "Rice"]), ("Meal 2", ["Pasta", "Bread"]))
    assert main_choices(day) == ["Curry", "Pasta"]


def test_the_same_main_twice_is_listed_once() -> None:
    day = _day(("Meal 1", ["Pasta"]), ("Meal 2", ["Pasta"]))
    assert summary(day) == "Pasta"


def test_unknown_layout_falls_back_to_the_first_dish() -> None:
    day = _day(("Empty", []), ("Lunch", ["Soup", "Roll"]))
    assert main_choices(day) == ["Soup"]
    assert main_choices(_day()) == []


def test_long_states_are_cut() -> None:
    day = _day(("Main Courses", ["x" * 200, "y" * 200]))
    text = summary(day)
    assert len(text) == MAX_STATE
    assert text.endswith("...")


def test_describe_skips_empty_courses() -> None:
    day = _day(("Meal 1", ["Curry", "Rice"]), ("Drinks", []))
    assert describe(day) == "Meal 1: Curry, Rice"


def test_describe_marks_unchecked_dishes() -> None:
    day = Day(
        DAY,
        (
            Course(
                "Meal 1",
                (
                    Dish("Macaroni Cheese", url="u/mac", contains_allergens=True),
                    Dish("Peas", url="u/peas"),
                    Dish("Bread", url="u/bread", contains_allergens=True),
                ),
            ),
        ),
    )
    text = describe(day, {"u/bread": ("Gluten",)}, mark_unchecked=True)
    assert (
        text == "Meal 1: Macaroni Cheese (allergens not checked), Peas, Bread (Gluten)"
    )
    # Without the flag (allergens off) nothing is added
    assert describe(day) == "Meal 1: Macaroni Cheese, Peas, Bread"
