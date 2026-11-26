"""Match the council's allergen names to the UK's 14, and check a day's menu.

No Home Assistant imports. The dish pages spell allergens freely ("Egg" and
"Eggs", "Sulphite" and "Sulphites", "Gluten" and "Wheat" side by side), so
names are matched by pattern, not exact text.

This only reads what the council publishes. "May contain" warnings appear on
some dish pages only (for example "May contain Sesame", which matches sesame),
and it never says a dish is safe: a dish marked as containing allergens whose
names are not known counts as unknown.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from .models import Day


class Allergen(StrEnum):
    """The 14 allergens UK food law requires caterers to declare."""

    CELERY = "celery"
    GLUTEN = "gluten"
    CRUSTACEANS = "crustaceans"
    EGGS = "eggs"
    FISH = "fish"
    LUPIN = "lupin"
    MILK = "milk"
    MOLLUSCS = "molluscs"
    MUSTARD = "mustard"
    PEANUTS = "peanuts"
    SESAME = "sesame"
    SOYA = "soya"
    SULPHITES = "sulphites"
    TREE_NUTS = "tree_nuts"


# Whole words only, so "Coconut" is not a nut and "Shellfish" is not a fish.
_PATTERNS: dict[Allergen, re.Pattern[str]] = {
    allergen: re.compile(rf"\b(?:{words})\b", re.I)
    for allergen, words in {
        Allergen.CELERY: r"celery|celeriac",
        Allergen.GLUTEN: r"gluten|wheat|barley|rye|oats?|spelt|kamut",
        Allergen.CRUSTACEANS: (
            r"crustaceans?|shellfish|prawns?|shrimps?|crabs?|lobsters?|langoustines?"
        ),
        Allergen.EGGS: r"eggs?",
        Allergen.FISH: r"fish",
        Allergen.LUPIN: r"lupin|lupine",
        Allergen.MILK: r"milk|dairy|lactose",
        Allergen.MOLLUSCS: (
            r"molluscs?|shellfish|mussels?|oysters?|squid|scallops?|clams?|octopus"
        ),
        Allergen.MUSTARD: r"mustard",
        Allergen.PEANUTS: r"peanuts?|ground ?nuts?|arachis",
        Allergen.SESAME: r"sesame",
        Allergen.SOYA: r"soya|soy|soybeans?",
        Allergen.SULPHITES: r"sulph?ites?|sulfites?|sulphur dioxide|sulfur dioxide",
        Allergen.TREE_NUTS: (
            r"(?<!pea)(?<!ground )nuts?|tree ?nuts?|almonds?|hazelnuts?|walnuts?|"
            r"cashews?|pecans?|brazil ?nuts?|pistachios?|macadamias?"
        ),
    }.items()
}


def allergens_in(name: str) -> set[Allergen]:
    """Which of the 14 a council allergen name refers to, e.g. "Wheat" is gluten."""
    return {allergen for allergen, pattern in _PATTERNS.items() if pattern.search(name)}


@dataclass(frozen=True, slots=True)
class DayCheck:
    """Watched allergens on one day's menu."""

    contains: dict[str, list[str]] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)

    @property
    def alert(self) -> bool | None:
        """True if a dish has one; None if only unknowns; False if neither."""
        if self.contains:
            return True
        return None if self.unknown else False


def check_day(
    day: Day,
    watch: Iterable[Allergen],
    allergens_for: Callable[[str], tuple[str, ...] | None],
) -> DayCheck:
    """Dishes on day that list a watched allergen, and dishes we cannot tell.

    allergens_for(url) returns the council's allergen names for a dish page,
    or None when the page has not been read.
    """
    watched = set(watch)
    contains: dict[str, list[str]] = {}
    unknown: list[str] = []
    for course in day.courses:
        for dish in course.dishes:
            names = allergens_for(dish.url) if dish.url else None
            if names is None:
                # No dish page read: only a dish the council flags (or one
                # that says to ask about allergens) is in doubt.
                if dish.contains_allergens or "allergen" in dish.name.lower():
                    if dish.name not in unknown:
                        unknown.append(dish.name)
                continue
            hits = [name for name in names if allergens_in(name) & watched]
            if hits:
                contains.setdefault(dish.name, [])
                contains[dish.name].extend(
                    h for h in hits if h not in contains[dish.name]
                )
    return DayCheck(contains=contains, unknown=unknown)
