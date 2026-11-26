"""Read a council menu page into a Week. No Home Assistant imports.

Every menu page uses the same template: a heading with the cycle week and the
date range, then one table per day with one row per course:

    <h2><span>This weeks menu : </span>Primary Week 3
        <div class="small"><span>26th</span>- 31st October 2026</div></h2>
    <table class="school-menu-table ...">
      <thead><tr><th>Monday</th></tr></thead>
      <tbody><tr>
        <th class="school-menu-item-heading ...">Meal 1</th>
        <td><div class="menu-item-entry">
          <a href="/.../meals/main/vegetable-curry">Vegetable Curry</a>
          <sup title="Suitable for vegetarians">V</sup>
          <sup title="Contains allergens">A</sup>
        </div></td>
      </tr></tbody>
    </table>

Outside the academic year the page says "No Menu for this date" and has no
tables, which is a normal empty result.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .dates import cycle_week_number, monday_of, parse_date_range, week_start_from_range
from .models import BASE_URL, Course, Day, Dish, Menu, Week

DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday")
NO_MENU_TEXT = "no menu for this date"
VEGETARIAN_TITLE = "suitable for vegetarians"
ALLERGENS_TITLE = "contains allergens"


class ParseError(Exception):
    """The page does not look like a menu page any more."""


def _text(node: Tag) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _heading(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """The cycle week label and the date range text from the heading."""
    for h2 in soup.find_all("h2"):
        span = h2.find("span")
        if span is None or not _text(span).lower().startswith("this weeks menu"):
            continue
        small = h2.find("div", class_="small")
        range_text = _text(small) if small else None
        parts = [
            str(s).strip()
            for s in h2.find_all(string=True, recursive=False)
            if str(s).strip()
        ]
        label = " ".join(" ".join(parts).split()) or None
        return label, range_text
    return None, None


def _dish(entry: Tag) -> Dish | None:
    titles = {(sup.get("title") or "").strip().lower() for sup in entry.find_all("sup")}
    for sup in entry.find_all("sup"):
        sup.decompose()
    name = _text(entry)
    if not name:
        return None
    link = entry.find("a", href=True)
    return Dish(
        name=name,
        url=urljoin(BASE_URL, link["href"]) if link else None,
        vegetarian=VEGETARIAN_TITLE in titles,
        contains_allergens=ALLERGENS_TITLE in titles,
    )


def _courses(table: Tag) -> tuple[Course, ...]:
    courses: list[Course] = []
    body = table.find("tbody") or table
    for row in body.find_all("tr"):
        heading = row.find("th", class_="school-menu-item-heading")
        cell = row.find("td")
        if heading is None or cell is None:
            continue
        dishes = tuple(
            dish
            for entry in cell.find_all("div", class_="menu-item-entry")
            if (dish := _dish(entry)) is not None
        )
        courses.append(Course(name=_text(heading), dishes=dishes))
    return tuple(courses)


def _weekday(table: Tag) -> int | None:
    head = table.find("thead")
    candidates = [_text(head)] if head else []
    caption = table.find("caption")
    if caption:
        candidates.append(_text(caption))
    for text in candidates:
        for word in re.findall(r"[A-Za-z]+", text.lower())[::-1]:
            if word in DAY_NAMES:
                return DAY_NAMES.index(word)
    return None


def parse_week(html: str, menu: Menu, requested: date) -> Week | None:
    """Parse a menu page fetched for the week holding requested.

    Returns None when the page has no menu for that date. Raises ParseError
    when the page has neither tables nor the "no menu" notice.
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", class_="school-menu-table")
    if not tables:
        if NO_MENU_TEXT in soup.get_text(" ").lower():
            return None
        raise ParseError(f"No menu tables on the {menu.label} page")

    label, range_text = _heading(soup)
    page_range = parse_date_range(range_text)
    monday = (
        week_start_from_range(page_range[0]) if page_range else monday_of(requested)
    )

    days: list[Day] = []
    for table in tables:
        weekday = _weekday(table)
        if weekday is None:
            raise ParseError(f"A {menu.label} menu table has no weekday")
        days.append(Day(date=monday + timedelta(days=weekday), courses=_courses(table)))
    days.sort(key=lambda d: d.date)

    return Week(
        menu=menu,
        monday=monday,
        label=label,
        cycle_week=cycle_week_number(label),
        days=tuple(days),
    )
