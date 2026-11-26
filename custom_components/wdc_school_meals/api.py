"""HTTP client for the council's menu and term dates pages. No HA imports."""

from __future__ import annotations

from datetime import date

from aiohttp import ClientError, ClientSession, ClientTimeout

from .dates import monday_of
from .models import BASE_URL, Menu, Week
from .parser import parse_week

USER_AGENT = (
    "ha-wdc-school-meals (+https://github.com/AndrewBarber/ha-wdc-school-meals)"
)
TIMEOUT = ClientTimeout(total=30)


class WdcConnectionError(Exception):
    """The council site could not be reached or answered with an error."""


class WdcClient:
    """Fetch and parse pages from west-dunbarton.gov.uk."""

    def __init__(self, session: ClientSession, base_url: str = BASE_URL) -> None:
        self._session = session
        self._base_url = base_url

    async def get_page(self, path: str, params: dict[str, str] | None = None) -> str:
        """Fetch a page by path. Raises WdcConnectionError."""
        try:
            async with self._session.get(
                f"{self._base_url}{path}",
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    raise WdcConnectionError(f"HTTP {resp.status} for {path}")
                return await resp.text()
        except (ClientError, TimeoutError) as err:
            raise WdcConnectionError(f"{type(err).__name__} for {path}") from err

    async def fetch_week(self, menu: Menu, day: date) -> Week | None:
        """The menu week holding day, or None outside the academic year.

        Raises WdcConnectionError or parser.ParseError.
        """
        monday = monday_of(day)
        html = await self.get_page(menu.path, {"date": monday.strftime("%d-%m-%Y")})
        return parse_week(html, menu, monday)
