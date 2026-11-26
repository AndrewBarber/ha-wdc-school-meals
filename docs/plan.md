# Plan: West Dunbartonshire School Meals for HACS

28 October 2026. Based on `research.md` and a review of the original
integration (`wdc_school_menu`, a YAML sensor for the primary menu). v0.1.0 and
the v0.2.0 items below are built (apart from the HACS default list); the commits are listed at the end.

## Decisions

| Question | Proposal |
| --- | --- |
| Domain | `wdc_school_meals` (new; the old `wdc_school_menu` keeps running alongside until the switch) |
| Repo | `AndrewBarber/ha-wdc-school-meals` (public from 26 Nov 2026) |
| Display name | "West Dunbartonshire School Meals", marked unofficial in the README |
| Licence | MIT |
| Brand | Our own simple plate and cutlery icon in `brand/`, not the council crest |
| Minimum HA | 2026.3.0 (local `brand/` folder support) |
| Rewrite | Clean rewrite. Old code is only a reference for behaviour and dashboard needs |
| One entry per child, or subentries | One "West Dunbartonshire School Meals" entry with a subentry per child ("Add child"), each with its own device. Fetching is then shared inside one entry with no `hass.data` plumbing. Fallback: one config entry per child, same entities |

## Scope

**v0.1.0 (first HACS release)**

- Config flow: pick a school by name (or a menu directly). Several entries per
  install, one per child, each with its own device and entities.
- All five menus: Nursery, Primary, Secondary, Kilpatrick Primary, Kilpatrick High.
- Today and next school day sensors, a lunch calendar, a school day binary sensor.
- Term dates, so holidays and in-service days show "No school" instead of a menu.
- Tests, CI (hassfest, HACS validation, ruff, pytest), README, licence, brand.

**v0.2.0**

- Named allergens and ingredients from the dish pages (opt in, cached).
- `wdc_school_meals.get_menu` action with a response, for automations and Assist.
- Allergen watch list per child (the UK 14), with two sensors that flag a day
  whose menu lists one; unknown when a dish cannot be checked, never "safe".
- Submit to the HACS default list.

**Not possible**: per school substitutions or Grab and Go picks (not published).

## Config flow

1. **School**: a searchable list of every council school and nursery, grouped by
   stage, plus "Choose a menu instead". `schools.py` holds the list with a
   `checked` date, built from the school pages.
2. **Stage** (only when one school maps to more than one menu): Kilpatrick
   Schools asks Primary or High; Choices School asks Secondary or Kilpatrick High.
3. **Who it is for** (optional): a name such as "Alex". The device is then
   "Alex's School Meals" (naming rule: things that belong to someone), else
   "<School> School Meals".

- Unique ID: school slug plus name, so the same school can be added for two
  children but not twice for one.
- Reconfigure flow to change school (P7 to S1) without losing entities.
- Options: calendar weeks ahead (1 to 4, default 2).
- Private funded nurseries are left out (no council menu). KEYS is listed under
  Kilpatrick, flagged as unconfirmed.

With subentries, the flow above is the "Add child" subentry flow; the main
entry has no questions.

## Worth keeping from the old code

- `dates.py` logic: the heading range parser (month and year roll over,
  "Sept", hyphen or en dash) and the rule that a range starting at the weekend
  belongs to the next week. Ported with its tests.
- The saved pages under `tests/fixtures/wdc_school_menu` (27 Oct) as extra
  primary fixtures.
- Nothing else: the line splitting, footer phrases and YAML platform go.

## Data layer (plain Python, no HA imports, fully unit tested)

| Module | Job |
| --- | --- |
| `api.py` | aiohttp client. `fetch_week(menu, day)` uses `?date=DD-MM-YYYY`. User-Agent names the repo |
| `parser.py` | Reads the day tables: course headings, dishes, slug, link, vegetarian and contains-allergens flags, cycle week, Monday date |
| `terms.py` | Parses the term dates pages into closures: holiday ranges, in-service days, single days |
| `schools.py` | Static school to menu map |
| `models.py` | Dataclasses: `Week`, `Day`, `Course`, `Dish`, `Closure` |

- **One coordinator per menu, shared** by every entry that uses it, so two
  primary children cost the same requests as one. Lives in `hass.data`, entries
  hold it in `entry.runtime_data`.
- Refresh every 6 hours, plus just after midnight so "today" rolls over. Needs
  this week and next week; a fetched week is reused for 12 hours, term dates
  for a day.
- Out of range dates ("No Menu for this date") are a normal empty result, not
  an error. A page with no tables during term raises `UpdateFailed` and, after a
  day of failures, a repair issue ("menu page layout changed").
- `beautifulsoup4==4.13.3`, the same pin as Core's `scrape`, so nothing extra
  installs.

## Entities (per entry, one service device)

| Entity | State | Attributes |
| --- | --- | --- |
| `sensor.<device>_today` | Main choices, e.g. "Vegetable Curry or Macaroni Cheese"; "No school" on closed days | `date`, `cycle_week`, `courses` (name to dishes, with flags), `url` |
| `sensor.<device>_next_school_day` | Same, for the next open day (Friday shows Monday) | Same plus `date` |
| `calendar.<device>_lunches` | On during a lunch (all day event), else off | One all day event per school day, summary is the main choices, description the full menu. Weeks beyond the cache are fetched on demand |
| `binary_sensor.<device>_school_day` | On when school is open today | `next_closure`, `closure_reason` |
| `sensor.<device>_cycle_week` | 1, 2 or 3 (diagnostic) | |

- `has_entity_name`, `translation_key` names, `icons.json`, entities go
  unavailable on failure and log once.
- Device: identifiers `(wdc_school_meals, entry_id)`, manufacturer "West
  Dunbartonshire Council" (data source), model is the menu name, service entry
  type, `configuration_url` is the menu page. This fixes the 2027.8 warning.
- Diagnostics download with the last parsed week.
- Attributes stay small: today and next day only. Full weeks live in the calendar.

## Quality

- Aim for the Bronze quality scale rules plus most of Silver (config flow tests,
  unique IDs, runtime data, unavailable handling, parallel updates, reconfigure,
  diagnostics).
- Tests: parser and term dates against saved pages for all five menus plus a
  "No Menu" page, config flow, setup and unload, sensors over a midnight
  rollover and a Friday, calendar ranges, shared coordinator. Mocked HTTP only;
  CI never hits the council site.
- `scripts/refresh-fixtures` (shell, curl) saves fresh pages when the layout
  changes.

## Repo layout

```
custom_components/wdc_school_meals/
  __init__.py  manifest.json  const.py  config_flow.py  coordinator.py
  api.py  parser.py  terms.py  schools.py  models.py  entity.py
  sensor.py  binary_sensor.py  calendar.py  diagnostics.py
  icons.json  translations/en.json  brand/icon.png (+ dark_icon, @2x)
tests/  fixtures/  conftest.py  test_*.py
.github/workflows/  validate.yml (hassfest, hacs/action)  tests.yml (ruff, pytest)  release.yml
hacs.json  README.md  LICENSE  CHANGELOG.md  pyproject.toml  requirements_test.txt
scripts/test  scripts/refresh-fixtures
docs/  research.md  plan.md
```

`hacs.json`: `name`, `country: "GB"`, `homeassistant: "2026.3.0"`,
`render_readme: true`. Releases are GitHub tags with notes; HACS installs from
the release.

## Being a good neighbour to the council site

- A few requests a day per menu, shared across entries: fetched weeks are kept
  for 12 hours and the refreshes reuse them. Dish pages (v0.2.0)
  only when opted in, cached for a week.
- No retries in a tight loop; back off on errors.

## Linear

Milestone **"3. WDC School Meals on HACS"** (renamed 28 Oct 2026). One issue
per branch, issue ID first in every commit. In build order:

| Issue | What | Blocked by |
| --- | --- | --- |
| AND-1709 | Repo scaffold, licence, hacs.json, CI | |
| AND-1710 | Table parser for all five menus, `?date` client, fixtures | AND-1709 |
| AND-1690 | Config flow, school picker, subentry per child, devices | AND-1710 |
| AND-1695 | Term dates, school day sensor, closures | AND-1710 |
| AND-1693 | Today and next school day sensors | AND-1690 |
| AND-1692 | Lunch calendar per child | AND-1690 |
| AND-1711 | README, brand icon, v0.1.0 release | |
| AND-1694 | Test on our HA side by side, switch the School view, retire the old one | AND-1692, AND-1693, AND-1695 |
| AND-1712 | v0.2.0: allergens and ingredients | |
| AND-1713 | v0.2.0: `get_menu` action | |
| AND-1714 | Later: HACS default list | |

## Commits and first release

v0.1.0 and the v0.2.0 items were built on 28 October 2026 but not committed
then. The per-issue commit plan was dropped. On 26 November 2026 (AND-2444) the
repo was published as one bootstrap commit for AND-1709 on `main`, then the
whole integration in one PR, and the first release was tagged `v0.2.0`. 0.1.0
was never released.
