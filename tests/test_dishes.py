"""Dish page parser."""

import pytest

from custom_components.wdc_school_meals.dishes import (
    DishDetails,
    Ingredient,
    parse_dish,
)
from custom_components.wdc_school_meals.parser import ParseError

from .pages import load_page

MEALS = (
    "https://www.west-dunbarton.gov.uk/schools-and-learning/schools/school-meals/meals"
)


def test_vegetarian_with_allergens() -> None:
    url = f"{MEALS}/main/macaroni-cheese"
    dish = parse_dish(load_page("dish-main-macaroni-cheese.html"), url)

    assert dish.name == "Macaroni Cheese"
    assert dish.vegetarian is True
    assert dish.allergens == ("Gluten", "Wheat", "Milk")
    assert dish.ingredients[0] == Ingredient("Macaroni", ("Gluten", "Wheat"))
    assert Ingredient("Cornflour", ()) in dish.ingredients


def test_no_allergens() -> None:
    dish = parse_dish(load_page("dish-side-dish-peas.html"), f"{MEALS}/side-dish/peas")
    assert dish.vegetarian is True
    assert dish.allergens == ()


def test_not_vegetarian() -> None:
    dish = parse_dish(
        load_page("dish-main-beef-burger-in-a-bun-with-cheese.html"),
        f"{MEALS}/main/beef-burger-in-a-bun-with-cheese",
    )
    assert dish.vegetarian is False
    assert "Sesame" in dish.allergens


def test_round_trips_through_storage() -> None:
    url = f"{MEALS}/main/macaroni-cheese"
    dish = parse_dish(load_page("dish-main-macaroni-cheese.html"), url)
    assert DishDetails.from_dict(dish.as_dict()) == dish


def test_not_a_dish_page() -> None:
    with pytest.raises(ParseError):
        parse_dish("<html><h1>Oops</h1></html>", f"{MEALS}/main/gone")
