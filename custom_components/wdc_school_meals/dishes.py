"""Read a dish page: vegetarian flag, allergens and ingredients. No HA imports.

Every dish on a menu links to its own page:

    <div class="menu-item">
      <h2>Macaroni Cheese</h2>
      <div class="meal-vegetarian">Suitable for vegetarians</div>
      <div><h3>Allergens</h3>Gluten, Wheat, Milk</div>
      <h3>Ingredients</h3>
      <table class="school-meal-ingredients">
        <tr><td>Macaroni</td><td>Gluten, Wheat</td></tr> ...

A dish with none says "Contains no allergens".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Tag

from .models import BASE_URL
from .parser import ParseError

if TYPE_CHECKING:
    from .api import WdcClient

NO_ALLERGENS = "contains no allergens"


@dataclass(frozen=True, slots=True)
class Ingredient:
    """One row of the ingredients table."""

    name: str
    allergens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DishDetails:
    """What a dish page says about the dish."""

    url: str
    name: str
    vegetarian: bool | None
    allergens: tuple[str, ...]
    ingredients: tuple[Ingredient, ...]

    def as_dict(self) -> dict[str, Any]:
        """For storage."""
        return {
            "url": self.url,
            "name": self.name,
            "vegetarian": self.vegetarian,
            "allergens": list(self.allergens),
            "ingredients": [[i.name, list(i.allergens)] for i in self.ingredients],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DishDetails:
        """From storage."""
        return cls(
            url=data["url"],
            name=data["name"],
            vegetarian=data["vegetarian"],
            allergens=tuple(data["allergens"]),
            ingredients=tuple(
                Ingredient(name, tuple(allergens))
                for name, allergens in data["ingredients"]
            ),
        )


def _text(node: Tag) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _split(text: str) -> tuple[str, ...]:
    if not text or text.lower() == NO_ALLERGENS:
        return ()
    return tuple(part.strip() for part in text.split(",") if part.strip())


def parse_dish(html: str, url: str) -> DishDetails:
    """Parse a dish page. Raises ParseError if it is not one."""
    soup = BeautifulSoup(html, "html.parser")
    item = soup.find("div", class_="menu-item")
    heading = item.find("h2") if item else None
    if item is None or heading is None:
        raise ParseError(f"Not a dish page: {url}")

    vegetarian: bool | None = None
    veg = item.find("div", class_="meal-vegetarian")
    if veg:
        vegetarian = not _text(veg).lower().startswith("not")

    allergens: tuple[str, ...] = ()
    for h3 in item.find_all("h3"):
        if _text(h3).lower() == "allergens" and h3.parent is not None:
            h3_text = _text(h3)
            allergens = _split(_text(h3.parent).removeprefix(h3_text).strip())
            break

    ingredients: list[Ingredient] = []
    table = item.find("table", class_="school-meal-ingredients")
    if table:
        for row in (table.find("tbody") or table).find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2 and _text(cells[0]):
                ingredients.append(Ingredient(_text(cells[0]), _split(_text(cells[1]))))

    return DishDetails(
        url=url,
        name=_text(heading),
        vegetarian=vegetarian,
        allergens=allergens,
        ingredients=tuple(ingredients),
    )


async def fetch_dish(client: WdcClient, url: str) -> DishDetails:
    """Fetch and parse one dish page. Raises WdcConnectionError or ParseError."""
    return parse_dish(await client.get_page(url.removeprefix(BASE_URL)), url)
