"""A sensor per course, today and on the next school day."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.wdc_school_meals.const import CONF_ALLERGENS
from custom_components.wdc_school_meals.models import MENU_COURSES, Menu, course_key

from .conftest import child, main_entry, setup_entry


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("Starter/Dessert", "starter_dessert"),
        ("Meal 1", "meal_1"),
        ("Grab and Go", "grab_and_go"),
        ("Snack AM", "snack_am"),
    ],
)
def test_course_key(name: str, key: str) -> None:
    assert course_key(name) == key


async def _setup(hass: HomeAssistant, menu: Menu, school: str, options=None) -> None:
    await setup_entry(hass, main_entry([child(menu, school, "Alex")], options))


@pytest.mark.usefixtures("mock_wdc")
async def test_primary_courses(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, Menu.PRIMARY, "balloch-primary-school")

    starter = hass.states.get("sensor.alex_school_meals_today_starter_dessert")
    assert starter.state == "Fresh Bread, Fresh Fruit Platter, Oatie Biscuits"
    assert starter.attributes["friendly_name"] == (
        "Alex's School Meals Today starter/dessert"
    )
    assert starter.attributes["course"] == "Starter/Dessert"
    assert "always check" in starter.attributes["attribution"]
    assert starter.attributes["date"] == "2026-10-28"
    assert starter.attributes["vegetarian"] == [
        "Fresh Bread",
        "Fresh Fruit Platter",
        "Oatie Biscuits",
    ]

    assert hass.states.get("sensor.alex_school_meals_today_drinks").state == (
        "Water, Milk"
    )
    meal_1 = hass.states.get("sensor.alex_school_meals_today_meal_1")
    assert meal_1.state == (
        "Beef Burger in a Bun with optional Cheese, Herby Diced Potatoes, "
        "Sweetcorn, Salad Bar"
    )
    upcoming = hass.states.get(
        "sensor.alex_school_meals_next_school_day_starter_dessert"
    )
    assert upcoming.state == "Fresh Bread, Fresh Fruit Platter, Lentil Soup"
    assert upcoming.attributes["date"] == "2026-10-29"

    # Exactly the primary rows, for both days
    registry = er.async_get(hass)
    ids = {
        e.entity_id
        for e in registry.entities.values()
        if e.entity_id.startswith("sensor.alex_school_meals_today_")
    }
    assert ids == {
        f"sensor.alex_school_meals_today_{key}" for key in MENU_COURSES[Menu.PRIMARY]
    }


@pytest.mark.usefixtures("mock_wdc")
async def test_secondary_courses(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, Menu.SECONDARY, "dumbarton-academy")

    assert hass.states.get("sensor.alex_school_meals_today_main_courses").state == (
        "Cheese Baked Vegetarian Pasta, Bubble Salmon"
    )
    assert hass.states.get("sensor.alex_school_meals_today_vegetables").state == "Peas"
    assert hass.states.get("sensor.alex_school_meals_today_drinks") is None


@pytest.mark.usefixtures("mock_wdc")
async def test_closed_today(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-31 10:00:00+00:00")  # Saturday
    await _setup(hass, Menu.PRIMARY, "balloch-primary-school")

    assert hass.states.get("sensor.alex_school_meals_today_drinks").state == (
        "No school"
    )
    upcoming = hass.states.get("sensor.alex_school_meals_next_school_day_drinks")
    assert upcoming.state == "Water, Milk"
    assert upcoming.attributes["date"] == "2026-11-02"


@pytest.mark.usefixtures("mock_dishes")
async def test_named_allergens_per_course(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, Menu.PRIMARY, "balloch-primary-school", {CONF_ALLERGENS: True})

    meal_1 = hass.states.get("sensor.alex_school_meals_today_meal_1")
    assert (
        "Milk"
        in meal_1.attributes["allergens"]["Beef Burger in a Bun with optional Cheese"]
    )
