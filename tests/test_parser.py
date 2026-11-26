"""Menu page parser, against pages saved from the council site."""

from datetime import date

import pytest

from custom_components.wdc_school_meals.models import Menu
from custom_components.wdc_school_meals.parser import ParseError, parse_week

from .pages import load_page

WEDNESDAY = date(2026, 10, 28)


@pytest.mark.parametrize(
    ("menu", "page", "label", "courses"),
    [
        (
            Menu.PRIMARY,
            "primary-menus-26-10-2026.html",
            "Primary Week 3",
            ["Starter/Dessert", "Meal 1", "Meal 2", "Drinks"],
        ),
        (
            Menu.SECONDARY,
            "secondary-menus-26-10-2026.html",
            "Secondary Week 3",
            [
                "Starter/Dessert",
                "Main Courses",
                "Sides",
                "Vegetables",
                "Grab and Go",
                "Snacks",
            ],
        ),
        (
            Menu.NURSERY,
            "nursery-menus-26-10-2026.html",
            "Nursery Week 3",
            [
                "Starter/Dessert",
                "Meal 1",
                "Meal 2",
                "Drinks",
                "Snack AM",
                "Snack PM",
            ],
        ),
        (
            Menu.KILPATRICK_PRIMARY,
            "kilpatrick-primary-school-26-10-2026.html",
            "Kilpatrick Primary Week 3",
            ["Starter/Dessert", "Meal 1", "Meal 2", "Drinks"],
        ),
        (
            Menu.KILPATRICK_HIGH,
            "kilpatrick-high-school-26-10-2026.html",
            "Kilpatrick High Week 3",
            [
                "Starter/Dessert",
                "Main Courses",
                "Sides",
                "Vegetables",
                "Grab and Go",
                "Snacks",
            ],
        ),
    ],
)
def test_every_menu(menu: Menu, page: str, label: str, courses: list[str]) -> None:
    week = parse_week(load_page(page), menu, WEDNESDAY)

    assert week is not None
    assert week.menu is menu
    assert week.label == label
    assert week.cycle_week == 3
    assert week.monday == date(2026, 10, 26)
    assert [d.date for d in week.days] == [
        date(2026, 10, 26),
        date(2026, 10, 27),
        date(2026, 10, 28),
        date(2026, 10, 29),
        date(2026, 10, 30),
    ]
    for day in week.days:
        assert [c.name for c in day.courses] == courses


def test_primary_dishes_and_flags() -> None:
    week = parse_week(
        load_page("primary-menus-26-10-2026.html"), Menu.PRIMARY, WEDNESDAY
    )
    assert week is not None
    wednesday = week.day(WEDNESDAY)
    assert wednesday is not None

    meal_1 = wednesday.course("Meal 1")
    assert meal_1 is not None
    burger = meal_1.dishes[0]
    assert burger.name == "Beef Burger in a Bun with optional Cheese"
    assert burger.url == (
        "https://www.west-dunbarton.gov.uk/schools-and-learning/schools/"
        "school-meals/meals/main/beef-burger-in-a-bun-with-cheese"
    )
    assert not burger.vegetarian
    assert burger.contains_allergens

    meal_2 = wednesday.course("Meal 2")
    assert meal_2 is not None
    assert meal_2.dishes[0].name == "Meat Free Mince"
    assert meal_2.dishes[0].vegetarian

    # Water has no dish page and no flags
    drinks = wednesday.course("Drinks")
    assert drinks is not None
    water, milk = drinks.dishes
    assert (water.name, water.url, water.vegetarian) == ("Water", None, False)
    assert milk.name == "Milk"
    assert milk.contains_allergens


def test_secondary_plain_text_dish() -> None:
    week = parse_week(
        load_page("secondary-menus-26-10-2026.html"), Menu.SECONDARY, WEDNESDAY
    )
    assert week is not None
    snacks = week.days[2].course("Snacks")
    assert snacks is not None
    assert snacks.dishes[0].name == (
        "Choice of toasted Paninis (please refer to catering staff for allergens)"
    )
    assert snacks.dishes[0].url is None


def test_next_weeks_cycle() -> None:
    week = parse_week(
        load_page("primary-menus-02-11-2026.html"), Menu.PRIMARY, date(2026, 11, 2)
    )
    assert week is not None
    assert (week.label, week.cycle_week) == ("Primary Week 1", 1)
    assert week.days[0].date == date(2026, 11, 2)


def test_week_across_the_year_end() -> None:
    week = parse_week(
        load_page("primary-menus-28-12-2026.html"), Menu.PRIMARY, date(2026, 12, 28)
    )
    assert week is not None
    assert week.monday == date(2026, 12, 28)
    assert week.days[-1].date == date(2027, 1, 1)


def test_no_menu_for_this_date() -> None:
    page = load_page("primary-menus-05-07-2027.html")
    assert parse_week(page, Menu.PRIMARY, date(2027, 7, 5)) is None


def test_no_range_falls_back_to_the_requested_week() -> None:
    page = load_page("primary-menus-26-10-2026.html").replace("- 31st October 2026", "")
    week = parse_week(page, Menu.PRIMARY, date(2026, 10, 28))
    assert week is not None
    assert week.monday == date(2026, 10, 26)


@pytest.mark.parametrize(
    "page",
    [
        "<html><body><h1>Primary Menus</h1></body></html>",
        "",
    ],
)
def test_unrecognised_page(page: str) -> None:
    with pytest.raises(ParseError):
        parse_week(page, Menu.PRIMARY, WEDNESDAY)


def test_table_without_a_weekday() -> None:
    page = '<table class="school-menu-table"><tbody></tbody></table>'
    with pytest.raises(ParseError):
        parse_week(page, Menu.PRIMARY, WEDNESDAY)
