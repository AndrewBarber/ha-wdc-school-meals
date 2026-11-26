"""Fetching and caching, shared by every child on the same menu."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import WdcClient, WdcConnectionError
from .const import (
    DISH_MAX_AGE,
    DOMAIN,
    TERMS_MAX_AGE,
    UPDATE_INTERVAL,
    WEEK_MAX_AGE,
    WEEKS_BACK,
)
from .dates import monday_of
from .dishes import DishDetails, fetch_dish
from .models import Day, Menu, Week
from .parser import ParseError
from .terms import TERM_DATES_PATH, SchoolCalendar, TermDatesError, fetch_school_years

if TYPE_CHECKING:
    from . import WdcSchoolMealsConfigEntry

_LOGGER = logging.getLogger(__name__)

ISSUE_TERM_DATES = "term_dates_unreadable"
DISH_STORE_VERSION = 1
DISH_STORE_KEY = f"{DOMAIN}.dishes"
DISH_FETCHES_AT_ONCE = 2


def _menu_issue(menu: Menu) -> str:
    return f"menu_layout_changed_{menu}"


class TermDates:
    """The school calendar, fetched at most once a day for every menu."""

    def __init__(self, hass: HomeAssistant, client: WdcClient) -> None:
        self._hass = hass
        self._client = client
        self._lock = asyncio.Lock()
        self._checked: datetime | None = None
        self.calendar = SchoolCalendar()

    async def async_refresh_if_stale(self) -> None:
        """Re-read the term dates pages when the last try is over a day old.

        Never raises: without term dates every weekday counts as open.
        """
        async with self._lock:
            now = dt_util.utcnow()
            if self._checked and now - self._checked < TERMS_MAX_AGE:
                return
            self._checked = now
            try:
                years = await fetch_school_years(self._client)
            except WdcConnectionError as err:
                _LOGGER.warning("Could not fetch the term dates: %s", err)
                return
            except TermDatesError as err:
                _LOGGER.warning("Could not read the term dates: %s", err)
                ir.async_create_issue(
                    self._hass,
                    DOMAIN,
                    ISSUE_TERM_DATES,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key=ISSUE_TERM_DATES,
                    translation_placeholders={
                        "url": f"https://www.west-dunbarton.gov.uk{TERM_DATES_PATH}"
                    },
                )
                return
            ir.async_delete_issue(self._hass, DOMAIN, ISSUE_TERM_DATES)
            self.calendar = SchoolCalendar(years)


class DishCache:
    """Dish pages (allergens, ingredients), kept on disk for a week.

    Only used when the allergens option is on. Shared by every menu, since
    many dishes appear on several menus.
    """

    def __init__(self, hass: HomeAssistant, client: WdcClient) -> None:
        self._client = client
        self._store: Store[dict[str, Any]] = Store(
            hass, DISH_STORE_VERSION, DISH_STORE_KEY
        )
        self._dishes: dict[str, tuple[datetime, DishDetails]] = {}
        self._limit = asyncio.Semaphore(DISH_FETCHES_AT_ONCE)

    async def async_load(self) -> None:
        """Read what earlier runs saved."""
        stored = await self._store.async_load() or {}
        for url, item in stored.get("dishes", {}).items():
            fetched = dt_util.parse_datetime(item["fetched"])
            if fetched:
                self._dishes[url] = (fetched, DishDetails.from_dict(item["dish"]))

    def get(self, url: str | None) -> DishDetails | None:
        """A cached dish, however old."""
        cached = self._dishes.get(url) if url else None
        return cached[1] if cached else None

    async def async_fetch(self, urls: Iterable[str]) -> None:
        """Fetch dishes not seen in the last week. Failures are skipped."""
        now = dt_util.utcnow()
        wanted = sorted(
            {
                url
                for url in urls
                if url not in self._dishes or now - self._dishes[url][0] > DISH_MAX_AGE
            }
        )
        if not wanted:
            return

        async def fetch(url: str) -> None:
            async with self._limit:
                try:
                    self._dishes[url] = (now, await fetch_dish(self._client, url))
                except (WdcConnectionError, ParseError) as err:
                    _LOGGER.debug("Skipping dish %s: %s", url, err)

        await asyncio.gather(*(fetch(url) for url in wanted))
        self._store.async_delay_save(self._data_to_save, 10)

    def _data_to_save(self) -> dict[str, Any]:
        return {
            "dishes": {
                url: {"fetched": fetched.isoformat(), "dish": dish.as_dict()}
                for url, (fetched, dish) in self._dishes.items()
            }
        }

    def __len__(self) -> int:
        return len(self._dishes)


@dataclass(frozen=True, slots=True)
class MenuSnapshot:
    """What the entities show, worked out on each refresh."""

    today: date
    today_menu: Day | None
    today_closure: str | None
    next_date: date | None
    next_menu: Day | None
    cycle_week: int | None
    next_closure: tuple[date, str] | None
    terms_known: bool
    weeks: dict[date, Week | None] = field(default_factory=dict)
    # Dish URL to its allergens, for today and the next school day. Empty
    # unless the allergens option is on.
    allergens: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


class MenuCoordinator(DataUpdateCoordinator[MenuSnapshot]):
    """One per menu in use. Holds a cache of fetched weeks."""

    config_entry: WdcSchoolMealsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WdcSchoolMealsConfigEntry,
        client: WdcClient,
        terms: TermDates,
        menu: Menu,
        dishes: DishCache | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {menu}",
            update_interval=UPDATE_INTERVAL,
        )
        self.menu = menu
        self.terms = terms
        self.dishes = dishes
        self._client = client
        self._weeks: dict[date, tuple[datetime, Week | None]] = {}
        # Roll today over just after midnight, not up to 6 hours later.
        entry.async_on_unload(
            async_track_time_change(hass, self._midnight, hour=0, minute=0, second=30)
        )

    @callback
    def _midnight(self, _now: datetime) -> None:
        self.hass.async_create_task(self.async_request_refresh())

    async def async_get_week(
        self, day: date, max_age: timedelta = WEEK_MAX_AGE
    ) -> Week | None:
        """The week holding day, from the cache when fresh enough.

        Raises WdcConnectionError or ParseError.
        """
        monday = monday_of(day)
        now = dt_util.utcnow()
        cached = self._weeks.get(monday)
        if cached and now - cached[0] < max_age:
            return cached[1]
        try:
            week = await self._client.fetch_week(self.menu, monday)
        except ParseError:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                _menu_issue(self.menu),
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="menu_layout_changed",
                translation_placeholders={
                    "menu": self.menu.label,
                    "url": self.menu.url,
                },
            )
            raise
        ir.async_delete_issue(self.hass, DOMAIN, _menu_issue(self.menu))
        self._weeks[monday] = (now, week)
        return week

    async def _async_update_data(self) -> MenuSnapshot:
        await self.terms.async_refresh_if_stale()
        calendar = self.terms.calendar
        today = dt_util.now().date()
        next_date = calendar.next_school_day(today)
        mondays = {monday_of(today), monday_of(today) + timedelta(days=7)}
        if next_date:
            mondays.add(monday_of(next_date))
        # Drop weeks the calendar can no longer show.
        oldest = monday_of(today) - timedelta(weeks=WEEKS_BACK)
        for monday in [m for m in self._weeks if m < oldest]:
            del self._weeks[monday]
        try:
            # Cached weeks are reused until WEEK_MAX_AGE, so the 6-hourly and
            # midnight refreshes only fetch what is missing or stale.
            weeks = {
                monday: await self.async_get_week(monday) for monday in sorted(mondays)
            }
        except WdcConnectionError as err:
            raise UpdateFailed(
                f"Could not fetch the {self.menu.label} menu: {err}"
            ) from err
        except ParseError as err:
            raise UpdateFailed(
                f"Could not read the {self.menu.label} menu: {err}"
            ) from err

        def menu_on(day: date | None) -> Day | None:
            week = weeks.get(monday_of(day)) if day else None
            return week.day(day) if week and day else None

        today_closure = calendar.closure_reason(today)
        today_menu = None if today_closure else menu_on(today)
        next_menu = menu_on(next_date)
        allergens: dict[str, tuple[str, ...]] = {}
        if self.dishes is not None:
            urls = [
                dish.url
                for day in (today_menu, next_menu)
                if day
                for course in day.courses
                for dish in course.dishes
                if dish.url
            ]
            await self.dishes.async_fetch(urls)
            for url in urls:
                if details := self.dishes.get(url):
                    allergens[url] = details.allergens

        this_week = weeks.get(monday_of(today))
        return MenuSnapshot(
            today=today,
            today_menu=today_menu,
            today_closure=today_closure,
            next_date=next_date,
            next_menu=next_menu,
            cycle_week=this_week.cycle_week if this_week else None,
            next_closure=calendar.next_closure(today),
            terms_known=calendar.known,
            weeks=weeks,
            allergens=allergens,
        )
