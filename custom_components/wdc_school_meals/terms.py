"""Term dates: which days the council schools are open. No HA imports.

The council's menu pages rotate the menu through holidays (the October break
and Christmas show menus), so open days come from the term dates pages
instead. Each academic year has its own page, linked from the index, with one
list item per line:

    Pupils Return: Monday 17 August 2026
    September week-end: Friday 25 September 2026 and Monday 28 September 2026
    Half-term - October Break: Monday 12 October 2026 - Friday 16 October 2026 (inclusive)
    In-service Day: Monday 9 November 2026*
    Schools close at 2.30 p.m. on Friday 18 December 2026
    Easter public holiday: Friday 26 March 2027 to Monday 29 March 2027
    Schools close at 1.00 p.m. Wednesday 30 June 2027

Early closes ("Schools close at 2.30 p.m.") still serve lunch. The latest
"Schools close" date is the last day of the year.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from .dates import MONTHS

if TYPE_CHECKING:
    from .api import WdcClient

TERM_DATES_PATH = "/schools-and-learning/schools/term-dates"
TERM_PAGE_RE = re.compile(rf"^{TERM_DATES_PATH}/term-dates?-\d{{6}}/?$")

# "Monday 12 October 2026", weekday optional
DATE_RE = re.compile(
    r"(?:(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+)?"
    r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})",
    re.I,
)
# Two dates joined by a dash or "to" are a range; "and" lists single days.
RANGE_JOINER_RE = re.compile(r"^\s*(?:-|–|to)\s*$", re.I)

WEEKEND = "Weekend"
SUMMER_HOLIDAYS = "Summer holidays"
NOT_LISTED = "Not on the term dates pages"
SEARCH_DAYS = 120


class TermDatesError(Exception):
    """A term dates page could not be read."""


@dataclass(frozen=True, slots=True)
class Closure:
    """Days the schools are shut, as listed on the term dates pages."""

    start: date
    end: date
    reason: str

    def covers(self, day: date) -> bool:
        """True if day falls inside this closure."""
        return self.start <= day <= self.end


@dataclass(frozen=True, slots=True)
class SchoolYear:
    """One academic year: first and last pupil days, and closures between."""

    first_day: date
    last_day: date
    closures: tuple[Closure, ...]


def _dates(text: str) -> list[tuple[date, int, int]]:
    """Every date in text, with where it starts and ends."""
    found = []
    for m in DATE_RE.finditer(text):
        month = MONTHS.get(m.group(2).lower())
        if month is None:
            continue
        try:
            found.append((date(int(m.group(3)), month, int(m.group(1))), *m.span()))
        except ValueError:
            continue
    return found


def _spans(text: str) -> list[tuple[date, date]]:
    """Dates in a line as (start, end) spans: ranges joined, singles alone."""
    found = _dates(text)
    spans: list[tuple[date, date]] = []
    i = 0
    while i < len(found):
        start, _, start_end = found[i]
        if i + 1 < len(found):
            end, end_start, _ = found[i + 1]
            if RANGE_JOINER_RE.match(text[start_end:end_start]) and end >= start:
                spans.append((start, end))
                i += 2
                continue
        spans.append((start, start))
        i += 1
    return spans


def _reason(label: str) -> str:
    """Tidy a line's label: "In-service Day" from "In-service Day*"."""
    return " ".join(label.replace("*", "").split()).rstrip(":").strip()


def parse_term_dates(html: str) -> SchoolYear:
    """Read one academic year's page. Raises TermDatesError."""
    soup = BeautifulSoup(html, "html.parser")
    first_day: date | None = None
    last_day: date | None = None
    closures: list[Closure] = []

    for item in soup.find_all("li"):
        text = " ".join(item.get_text(" ", strip=True).split())
        spans = _spans(text)
        if not spans:
            continue
        label, _, _ = text.partition(":")
        lower = text.lower()
        if lower.startswith("pupils return"):
            first_day = spans[0][0]
        elif lower.startswith("schools close"):
            last_day = max(last_day or spans[0][0], spans[0][0])
        elif lower.startswith(("schools re-open", "schools return")):
            continue
        elif ":" in text:
            reason = _reason(label)
            closures.extend(Closure(start, end, reason) for start, end in spans)

    if first_day is None or last_day is None or last_day <= first_day:
        raise TermDatesError("No pupils return or schools close date on the page")
    return SchoolYear(
        first_day=first_day,
        last_day=last_day,
        closures=tuple(sorted(closures, key=lambda c: c.start)),
    )


def term_dates_links(html: str) -> list[str]:
    """Paths of the per-year pages linked from the term dates index."""
    soup = BeautifulSoup(html, "html.parser")
    links = {
        a["href"].rstrip("/")
        for a in soup.find_all("a", href=True)
        if TERM_PAGE_RE.match(a["href"])
    }
    if not links:
        raise TermDatesError("No term dates pages linked from the index")
    return sorted(links)


async def fetch_school_years(client: WdcClient) -> list[SchoolYear]:
    """Every academic year on the council site, oldest first.

    Raises api.WdcConnectionError or TermDatesError.
    """
    index = await client.get_page(TERM_DATES_PATH)
    pages = await asyncio.gather(
        *(client.get_page(path) for path in term_dates_links(index))
    )
    return sorted((parse_term_dates(page) for page in pages), key=lambda y: y.first_day)


class SchoolCalendar:
    """Answers "is school open on this day, and if not, why?".

    With no years (term dates unreadable) every weekday counts as open, so the
    menus still show.
    """

    def __init__(self, years: Iterable[SchoolYear] = ()) -> None:
        self.years = tuple(sorted(years, key=lambda y: y.first_day))

    @property
    def known(self) -> bool:
        """True when term dates were read."""
        return bool(self.years)

    def closure_reason(self, day: date) -> str | None:
        """None if school is open on day, else why it is shut."""
        if day.weekday() >= 5:
            return WEEKEND
        if not self.years:
            return None
        for year in self.years:
            if year.first_day <= day <= year.last_day:
                closure = next((c for c in year.closures if c.covers(day)), None)
                return closure.reason if closure else None
        # Outside every year: between two years, or the summer before the
        # first or after the last one listed.
        if self.years[0].first_day < day < self.years[-1].last_day or day.month in (
            6,
            7,
            8,
        ):
            return SUMMER_HOLIDAYS
        return NOT_LISTED

    def is_school_day(self, day: date) -> bool:
        """True if pupils are in on day."""
        return self.closure_reason(day) is None

    def next_school_day(self, after: date) -> date | None:
        """The first school day after the given day, within SEARCH_DAYS."""
        for offset in range(1, SEARCH_DAYS + 1):
            day = after + timedelta(days=offset)
            if self.is_school_day(day):
                return day
        return None

    def next_closure(self, after: date) -> tuple[date, str] | None:
        """The next weekday after the given day that school is shut, and why."""
        for offset in range(1, SEARCH_DAYS + 1):
            day = after + timedelta(days=offset)
            if day.weekday() < 5 and (reason := self.closure_reason(day)):
                return day, reason
        return None
