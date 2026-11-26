"""Config flow for West Dunbartonshire School Meals.

The main entry asks nothing. Each child is a subentry: pick a school (or a
menu), say who it is for, and pick the stage when a school has two menus.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from homeassistant.util import slugify

from .allergens import Allergen
from .const import (
    CONF_ALLERGENS,
    CONF_MENU,
    CONF_SCHOOL,
    CONF_WATCH,
    CONF_WEEKS_AHEAD,
    DEFAULT_WEEKS_AHEAD,
    DOMAIN,
    SUBENTRY_CHILD,
    TITLE,
)
from .models import Menu
from .schools import SCHOOLS, SCHOOLS_BY_SLUG


class WdcSchoolMealsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the single main entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm and create the entry."""
        if user_input is not None:
            return self.async_create_entry(title=TITLE, data={})
        return self.async_show_form(step_id="user")

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Children are subentries."""
        return {SUBENTRY_CHILD: ChildSubentryFlow}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Calendar range and allergens."""
        return WdcSchoolMealsOptionsFlow()


class WdcSchoolMealsOptionsFlow(OptionsFlow):
    """Options for the main entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Calendar weeks ahead, and whether to fetch dish allergens."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_WEEKS_AHEAD: int(user_input[CONF_WEEKS_AHEAD]),
                    CONF_ALLERGENS: bool(user_input.get(CONF_ALLERGENS, False)),
                }
            )
        options = self.config_entry.options
        current = options.get(CONF_WEEKS_AHEAD, DEFAULT_WEEKS_AHEAD)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WEEKS_AHEAD, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=4, step=1, mode=NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Required(
                        CONF_ALLERGENS, default=options.get(CONF_ALLERGENS, False)
                    ): BooleanSelector(),
                }
            ),
        )


def child_title(name: str | None, school: str | None, menu: Menu) -> str:
    """Device name: "Alex's School Meals", "Balloch Primary School Meals"."""
    if name:
        return f"{name}'s School Meals"
    if school:
        return f"{SCHOOLS_BY_SLUG[school].name} Meals"
    return f"{menu.label} School Meals"


def child_unique_id(name: str | None, school: str | None, menu: Menu) -> str:
    """Same school and name twice is a duplicate; two names is two children."""
    return f"{school or menu}:{slugify(name or '')}"


def _menu_selector(menus: list[Menu]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[menu.value for menu in menus],
            translation_key=CONF_MENU,
            mode=SelectSelectorMode.LIST,
        )
    )


def _name_field(default: str | None) -> dict[Any, Any]:
    key = (
        vol.Optional(CONF_NAME, description={"suggested_value": default})
        if default
        else vol.Optional(CONF_NAME)
    )
    return {key: TextSelector()}


class ChildSubentryFlow(ConfigSubentryFlow):
    """Add or change one child."""

    def __init__(self) -> None:
        self._name: str | None = None
        self._school: str | None = None
        self._menu: Menu | None = None

    def _current(self) -> dict[str, Any]:
        if self.source == SOURCE_RECONFIGURE:
            return dict(self._get_reconfigure_subentry().data)
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """By school or by menu."""
        return self.async_show_menu(step_id="user", menu_options=["school", "menu"])

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Same choices when changing a child, e.g. moving up to high school."""
        return self.async_show_menu(
            step_id="reconfigure", menu_options=["school", "menu"]
        )

    async def async_step_school(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pick a school from the council's list."""
        current = self._current()
        if user_input is not None:
            self._name = (user_input.get(CONF_NAME) or "").strip() or None
            self._school = user_input[CONF_SCHOOL]
            menus = SCHOOLS_BY_SLUG[self._school].menus
            if len(menus) > 1:
                return await self.async_step_stage()
            self._menu = menus[0]
            return await self.async_step_allergies()

        school_field = (
            vol.Required(CONF_SCHOOL, default=current[CONF_SCHOOL])
            if current.get(CONF_SCHOOL) in SCHOOLS_BY_SLUG
            else vol.Required(CONF_SCHOOL)
        )
        schema = {
            school_field: SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=school.slug, label=school.name)
                        for school in sorted(SCHOOLS, key=lambda s: s.name)
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            **_name_field(current.get(CONF_NAME)),
        }
        return self.async_show_form(step_id="school", data_schema=vol.Schema(schema))

    async def async_step_stage(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The school has more than one menu: which one does the child eat?"""
        assert self._school is not None
        school = SCHOOLS_BY_SLUG[self._school]
        if user_input is not None:
            self._menu = Menu(user_input[CONF_MENU])
            return await self.async_step_allergies()
        return self.async_show_form(
            step_id="stage",
            data_schema=vol.Schema(
                {vol.Required(CONF_MENU): _menu_selector(list(school.menus))}
            ),
            description_placeholders={"school": school.name},
        )

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pick one of the five menus directly."""
        current = self._current()
        if user_input is not None:
            self._name = (user_input.get(CONF_NAME) or "").strip() or None
            self._school = None
            self._menu = Menu(user_input[CONF_MENU])
            return await self.async_step_allergies()
        menu_field = (
            vol.Required(CONF_MENU, default=current[CONF_MENU])
            if current.get(CONF_MENU)
            else vol.Required(CONF_MENU)
        )
        schema = {
            menu_field: _menu_selector(list(Menu)),
            **_name_field(current.get(CONF_NAME)),
        }
        return self.async_show_form(step_id="menu", data_schema=vol.Schema(schema))

    async def async_step_allergies(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Allergens to watch for this child, if any."""
        if user_input is not None:
            return await self._async_finish(list(user_input.get(CONF_WATCH, [])))
        current = self._current().get(CONF_WATCH) or []
        return self.async_show_form(
            step_id="allergies",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_WATCH, default=current): SelectSelector(
                        SelectSelectorConfig(
                            options=[allergen.value for allergen in Allergen],
                            translation_key="allergen",
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def _async_finish(self, watch: list[str]) -> SubentryFlowResult:
        assert self._menu is not None
        menu = self._menu
        title = child_title(self._name, self._school, menu)
        unique_id = child_unique_id(self._name, self._school, menu)
        data = {
            CONF_NAME: self._name,
            CONF_SCHOOL: self._school,
            CONF_MENU: menu.value,
            CONF_WATCH: watch,
        }
        entry = self._get_entry()
        own_id = (
            self._get_reconfigure_subentry().subentry_id
            if self.source == SOURCE_RECONFIGURE
            else None
        )
        if any(
            sub.unique_id == unique_id and sub.subentry_id != own_id
            for sub in entry.subentries.values()
        ):
            return self.async_abort(reason="already_configured")
        if self.source == SOURCE_RECONFIGURE:
            return self.async_update_and_abort(
                entry,
                self._get_reconfigure_subentry(),
                title=title,
                data=data,
                unique_id=unique_id,
            )
        return self.async_create_entry(title=title, data=data, unique_id=unique_id)
