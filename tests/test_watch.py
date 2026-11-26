"""Allergen watch list: matching the council's names, and the sensors."""

import re
from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.wdc_school_meals.allergens import (
    Allergen,
    allergens_in,
    check_day,
)
from custom_components.wdc_school_meals.models import Course, Day, Dish, Menu

from .conftest import MEALS, child, main_entry, setup_entry

TODAY = "binary_sensor.alex_school_meals_watched_allergen_today"
NEXT = "binary_sensor.alex_school_meals_watched_allergen_next_school_day"
BURGER = "Beef Burger in a Bun with optional Cheese"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Gluten", {Allergen.GLUTEN}),
        ("Wheat", {Allergen.GLUTEN}),
        ("Egg", {Allergen.EGGS}),
        ("Eggs", {Allergen.EGGS}),
        ("Sulphite", {Allergen.SULPHITES}),
        ("Sulphites", {Allergen.SULPHITES}),
        ("Sulphur Dioxide", {Allergen.SULPHITES}),
        ("Milk", {Allergen.MILK}),
        ("Soya", {Allergen.SOYA}),
        ("Sesame", {Allergen.SESAME}),
        ("Celery", {Allergen.CELERY}),
        ("Mustard", {Allergen.MUSTARD}),
        ("Lupin", {Allergen.LUPIN}),
        ("Fish", {Allergen.FISH}),
        ("Peanuts", {Allergen.PEANUTS}),
        ("Peanut", {Allergen.PEANUTS}),
        ("Ground nuts", {Allergen.PEANUTS}),
        ("Nuts", {Allergen.TREE_NUTS}),
        ("Tree Nuts", {Allergen.TREE_NUTS}),
        ("Almonds", {Allergen.TREE_NUTS}),
        ("Hazelnut", {Allergen.TREE_NUTS}),
        ("Shellfish", {Allergen.CRUSTACEANS, Allergen.MOLLUSCS}),
        ("Coconut", set()),
        ("Contains no allergens", set()),
    ],
)
def test_allergens_in(name: str, expected: set[Allergen]) -> None:
    assert allergens_in(name) == expected


def _day(*dishes: Dish) -> Day:
    return Day(date(2026, 10, 28), (Course("Meal 1", dishes),))


def test_check_day() -> None:
    day = _day(
        Dish("Satay", url="u/satay", contains_allergens=True),
        Dish("Sponge", url="u/sponge", contains_allergens=True),
        Dish("Mystery", url="u/mystery", contains_allergens=True),
        Dish("Peas", url="u/peas"),
        Dish("Panini (please refer to catering staff for allergens)"),
        Dish("Water"),
    )
    known = {"u/satay": ("Peanuts",), "u/sponge": ("Eggs", "Nuts"), "u/peas": ()}

    check = check_day(day, [Allergen.PEANUTS, Allergen.TREE_NUTS], known.get)

    assert check.contains == {"Satay": ["Peanuts"], "Sponge": ["Nuts"]}
    # Flagged without names, or telling you to ask: unknown, never fine
    assert check.unknown == [
        "Mystery",
        "Panini (please refer to catering staff for allergens)",
    ]
    assert check.alert is True


def test_only_unknowns_is_not_off() -> None:
    day = _day(Dish("Mystery", url="u/mystery", contains_allergens=True))
    check = check_day(day, [Allergen.MILK], {}.get)
    assert check.alert is None


def test_nothing_watched_on_the_menu() -> None:
    day = _day(Dish("Peas", url="u/peas"), Dish("Water"))
    check = check_day(day, [Allergen.MILK], {"u/peas": ()}.get)
    assert check.alert is False


async def _setup(hass: HomeAssistant, watch: list[str]) -> None:
    await setup_entry(
        hass,
        main_entry([child(Menu.PRIMARY, "balloch-primary-school", "Alex", watch)]),
    )


@pytest.mark.usefixtures("mock_dishes")
async def test_on_when_a_dish_lists_one(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, ["sesame"])

    state = hass.states.get(TODAY)
    assert state.state == "on"
    assert (
        state.attributes["friendly_name"]
        == "Alex's School Meals Watched allergen today"
    )
    assert state.attributes["date"] == "2026-10-28"
    assert state.attributes["watching"] == ["sesame"]
    assert state.attributes["contains"] == {BURGER: ["Sesame"]}
    assert state.attributes["unknown"] == []
    assert state.attributes["device_class"] == "problem"


@pytest.mark.usefixtures("mock_dishes")
async def test_off_when_none_listed(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, ["celery"])

    assert hass.states.get(TODAY).state == "off"
    upcoming = hass.states.get(NEXT)
    assert upcoming.state == "off"
    assert upcoming.attributes["date"] == "2026-10-29"


async def test_unknown_when_a_flagged_dish_cannot_be_read(
    hass: HomeAssistant, mock_wdc: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    mock_wdc.get(f"{MEALS}/main/beef-burger-in-a-bun-with-cheese", status=500)
    mock_wdc.get(re.compile(re.escape(MEALS) + "/.*"), text="<p>no allergens here</p>")
    await _setup(hass, ["celery"])

    state = hass.states.get(TODAY)
    assert state.state == "unknown"
    assert BURGER in state.attributes["unknown"]


@pytest.mark.usefixtures("mock_dishes")
async def test_off_on_a_closed_day(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-11-09 10:00:00+00:00")  # in-service day
    await _setup(hass, ["sesame"])

    assert hass.states.get(TODAY).state == "off"
    assert hass.states.get(NEXT).attributes["date"] == "2026-11-10"


@pytest.mark.usefixtures("mock_dishes")
async def test_no_sensors_without_a_watch_list(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, [])

    registry = er.async_get(hass)
    assert registry.async_get(TODAY) is None
    assert registry.async_get(NEXT) is None


async def test_watching_reads_dish_pages_without_the_option(
    hass: HomeAssistant, mock_dishes: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-28 10:00:00+00:00")
    await _setup(hass, ["sesame"])

    assert any("/meals/" in str(url) for _, url, _, _ in mock_dishes.mock_calls)


def test_may_contain_counts() -> None:
    assert allergens_in("May contain Sesame") == {Allergen.SESAME}
