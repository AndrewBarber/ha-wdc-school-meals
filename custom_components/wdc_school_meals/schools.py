"""Council schools and nurseries, and the menu each one uses.

Built from the "Menu information" link on every school and nursery page on
west-dunbarton.gov.uk (school-search and early-years/find-elc), checked
28 October 2026. Menus differ by stage, not by school, so this is only a
lookup. Slugs are the council's page slugs.

Left out on purpose:
- Private funded nurseries (Acre Wood, Brookland, Carousel, Children's Hour,
  Great Start, Lucky Little Stars, Sunflower, Tots R Us, Villa Kindergarten):
  they do their own food.
- KEYS (Kilpatrick Early Years Service): its page links to the Kilpatrick High
  menu, which looks like a mistake. Use "Choose a menu instead".
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Menu

CHECKED = "2026-10-28"


@dataclass(frozen=True, slots=True)
class School:
    """A school and the menus it can use (more than one means ask)."""

    slug: str
    name: str
    menus: tuple[Menu, ...]


def _schools(menus: tuple[Menu, ...], *rows: tuple[str, str]) -> list[School]:
    return [School(slug, name, menus) for slug, name in rows]


_NURSERY = (Menu.NURSERY,)
_PRIMARY = (Menu.PRIMARY,)
_SECONDARY = (Menu.SECONDARY,)

SCHOOLS: tuple[School, ...] = (
    *_schools(
        _NURSERY,
        ("andrew-b-cameron", "Andrew B Cameron Early Learning and Childcare Centre"),
        (
            "balloch-nursery",
            "Balloch Primary School Early Learning and Childcare Centre",
        ),
        ("bellsmyre-nursery", "Bellsmyre Early Learning and Childcare Centre"),
        (
            "braehead-primary-nursery",
            "Braehead Primary Early Learning and Childcare Centre",
        ),
        ("brucehill-nursery", "Brucehill Early Learning and Childcare Centre"),
        ("carleith", "Carleith Primary School Early Learning and Childcare Centre"),
        ("christie-park-nursery", "Christie Park Early Learning and Childcare Centre"),
        ("clydebank-nursery", "Clydebank Early Learning and Childcare Centre"),
        ("dalmonach-nursery", "Dalmonach Early Learning and Childcare Centre"),
        ("dalmuir-nursery", "Dalmuir Early Learning and Childcare Centre"),
        (
            "dalreoch-elcc",
            "Dalreoch Primary School Early Learning and Childcare Centre",
        ),
        ("faifley-elcc", "Faifley Early Learning and Childcare Centre"),
        ("ferryfield-nursery", "Ferryfield Early Learning and Childcare Centre"),
        (
            "gartocharn-nursery",
            "Gartocharn Primary School Early Learning and Childcare Centre",
        ),
        (
            "gavinburn-nursery",
            "Gavinburn Primary School Early Learning and Childcare Centre",
        ),
        (
            "kilbowie-nursery",
            "Kilbowie Primary School Early Learning and Childcare Centre",
        ),
        ("ladyton-nursery", "Ladyton Early Learning and Childcare Centre"),
        (
            "lennox-nursery-alexandria",
            "Lennox Primary School Early Learning and Childcare Centre (Alexandria)",
        ),
        (
            "levenvale-nursery",
            "Levenvale Primary School Early Learning and Childcare Centre",
        ),
        (
            "linnvale-nursery",
            "Linnvale Primary School Early Learning and Childcare Centre",
        ),
        (
            "nursery-times-by-the-river",
            "Nursery Times by the River Early Learning and Childcare Centre",
        ),
        (
            "our-lady-of-loretto-primary-school-elcc",
            "Our Lady of Loretto Primary School Early Learning and Childcare Centre",
        ),
        (
            "renton-primary-school-and-elcc",
            "Renton Primary School Early Learning and Childcare Centre",
        ),
        (
            "st-eunans-nursery",
            "St Eunan's Primary School Early Learning and Childcare Centre",
        ),
        (
            "st-marys-alexandria",
            "St Mary's Primary School Early Learning and Childcare Centre (Alexandria)",
        ),
        (
            "st-marys-duntocher",
            "St Mary's Primary School Early Learning and Childcare Centre (Duntocher)",
        ),
        (
            "st-ronans-elcc",
            "St Ronan's Primary School Early Learning and Childcare Centre",
        ),
        ("whitecrook-nursery", "Whitecrook Early Learning and Childcare Centre"),
        (
            "whitecrook-primary-elcc",
            "Whitecrook Primary School Early Learning and Childcare Centre",
        ),
    ),
    *_schools(
        _PRIMARY,
        ("aitkenbar-primary-school", "Aitkenbar Primary School"),
        ("balloch-primary-school", "Balloch Primary School"),
        ("bonhill-primary-school", "Bonhill Primary School"),
        ("braehead-primary-school", "Braehead Primary School"),
        ("carleith-primary-school", "Carleith Primary School"),
        ("christie-park-primary-school", "Christie Park Primary School"),
        ("clydemuir-primary-school", "Clydemuir Primary School"),
        ("dalreoch-primary-school", "Dalreoch Primary School"),
        ("edinbarnet-primary-school", "Edinbarnet Primary School"),
        ("gartocharn-primary-school", "Gartocharn Primary School"),
        ("gavinburn-primary-school", "Gavinburn Primary School"),
        ("goldenhill-primary-school", "Goldenhill Primary School"),
        ("kilbowie-primary-school", "Kilbowie Primary School"),
        ("knoxland-primary-school", "Knoxland Primary School"),
        ("lennox-primary-school", "Lennox Primary School"),
        ("levenvale-primary-school", "Levenvale Primary School"),
        ("linnvale-primary-school", "Linnvale Primary School"),
        ("our-holy-redeemer-primary-school", "Our Holy Redeemer Primary School"),
        ("our-lady-of-loretto-primary-school", "Our Lady of Loretto Primary School"),
        ("renton-primary-school", "Renton Primary School"),
        ("st-eunans-primary-school", "St Eunan's Primary School"),
        ("st-josephs-primary-school", "St Joseph's Primary School"),
        ("st-kessogs-primary-school", "St Kessog's Primary School"),
        ("st-martins-primary-school", "St Martin's Primary School"),
        ("st-marys-primary-school-alexandria", "St Mary's Primary School (Alexandria)"),
        ("st-marys-primary-school-clydebank", "St Mary's Primary School (Clydebank)"),
        ("st-michaels-primary-school", "St Michael's Primary School"),
        ("st-patricks-primary-school", "St Patrick's Primary School"),
        ("st-peters-primary-school", "St Peter's Primary School"),
        ("st-ronans-primary-school", "St Ronan's Primary School"),
        ("st-stephens-primary-school", "St Stephen's Primary School"),
        ("whitecrook-primary-school", "Whitecrook Primary School"),
        ("cunard-school", "Cunard School"),
    ),
    *_schools(
        _SECONDARY,
        ("clydebank-high-school", "Clydebank High School"),
        ("dumbarton-academy", "Dumbarton Academy"),
        (
            "our-lady-and-saint-patricks-high-school",
            "Our Lady and Saint Patrick's High School",
        ),
        ("st-peter-the-apostle-high-school", "St Peter the Apostle High School"),
        ("vale-of-leven-academy", "Vale of Leven Academy"),
    ),
    # Additional support needs. Kilpatrick teaches primary and secondary ages;
    # Choices School links to both the secondary and Kilpatrick High menus.
    School(
        "kilpatrick-schools",
        "Kilpatrick Schools",
        (Menu.KILPATRICK_PRIMARY, Menu.KILPATRICK_HIGH),
    ),
    School("riverside-school", "Riverside School", (Menu.KILPATRICK_HIGH,)),
    School("choices-school", "Choices School", (Menu.SECONDARY, Menu.KILPATRICK_HIGH)),
)

SCHOOLS_BY_SLUG: dict[str, School] = {school.slug: school for school in SCHOOLS}
