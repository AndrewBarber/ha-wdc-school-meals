# West Dunbartonshire School Meals for Home Assistant

[![Validate](https://github.com/AndrewBarber/ha-wdc-school-meals/actions/workflows/validate.yml/badge.svg)](https://github.com/AndrewBarber/ha-wdc-school-meals/actions/workflows/validate.yml)
[![Tests](https://github.com/AndrewBarber/ha-wdc-school-meals/actions/workflows/tests.yml/badge.svg)](https://github.com/AndrewBarber/ha-wdc-school-meals/actions/workflows/tests.yml)
[![Buy me a beer](https://img.shields.io/badge/Buy%20me%20a%20beer%3F-5F7FFF?logo=buymeacoffee&logoColor=white&style=flat)](https://buymeacoffee.com/andrewbarber)

What's for lunch at school today? This integration reads the menus West
Dunbartonshire Council publishes and shows them in Home Assistant, per child.

## Before you rely on it

**This integration is unofficial and comes with no guarantees.** It is not
affiliated with or endorsed by West Dunbartonshire Council. It copies what the
council publishes on its website, which can be wrong, out of date or change on
the day, and it can fail to read the site correctly.

- **Always check menus and allergens with the school yourself.** Do not rely on
  this integration for decisions about allergies, intolerances or medical
  diets.
- A child with an adapted or medically prescribed diet may be served something
  other than the published menu.
- No sensor here, including "off" on an allergen sensor, means a dish is safe.

The MIT licence applies: the software is provided as is, without warranty.

## What you get

- Every council menu: **Nursery**, **Primary**, **Secondary**, and the
  **Kilpatrick Primary** and **Kilpatrick High** menus for Kilpatrick Schools
  and Riverside School.
- Pick your child's school by name. Add as many children as you like, each with
  their own device, for example "Alex's School Meals".
- Today's lunch and the next school day's lunch (Friday shows Monday).
- A lunch calendar that skips weekends, holidays and in-service days, read from
  the council's term dates.
- A school day sensor for other automations (alarms, heating, lights).
- Optional named allergens for each dish ("Gluten, Wheat, Milk"), from the
  council's dish pages.
- A **Get menu** action for any date, for automations and voice assistants.
- An optional allergen watch list per child, with sensors that flag a day whose
  menu lists one of them. Read the warning under **Allergen watch list**.

## Install

### HACS or Marketplace (custom repository)

From Home Assistant 2026.11, HACS is built in as **Settings > Marketplace**.
On older versions, use HACS. The steps are the same in both.

1. Open HACS (or Marketplace) > three dots > **Custom repositories**.
2. Add `https://github.com/AndrewBarber/ha-wdc-school-meals`, type **Integration**.
3. Find **West Dunbartonshire School Meals**, download it, and restart Home Assistant.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AndrewBarber&repository=ha-wdc-school-meals&category=integration)

### Manual

Copy `custom_components/wdc_school_meals` into your `config/custom_components/`
folder and restart Home Assistant.

Needs Home Assistant 2026.3 or newer.

## Set up

1. **Settings > Devices & services > Add integration > West Dunbartonshire
   School Meals.**
2. On the integration page, choose **Add child**.
3. **Pick their school** (council schools and nurseries are listed) or **pick a
   menu instead**. Kilpatrick Schools and Choices School ask which menu.
4. Optionally say who it is for. The device is then named "Alex's School
   Meals", otherwise after the school.

To move a child to high school, open the child and choose **Change school**.
Their entities stay the same.

Options:

- **Weeks ahead** (1 to 4, default 2): how far the calendars look.
- **Named allergens** (off by default): also read each dish's page. Adds an
  `allergens` attribute (dish to allergens) and puts them in brackets in
  calendar events. Dish pages are read for today and the next school day; on
  other days a flagged dish shows "(allergens not checked)". About 20 extra
  requests the first day, then a few a week; dish pages are kept for a week.

## Entities

For a child named Alex:

| Entity | State | Attributes |
| --- | --- | --- |
| `sensor.alex_school_meals_today` | The choices, e.g. "Vegetable Curry or Macaroni Cheese", or "No school" | `date`, `cycle_week`, `courses`, `vegetarian`, `contains_allergens`, `closure_reason`, `menu_url` |
| `sensor.alex_school_meals_next_school_day` | The next school day's choices | `date`, `courses`, `vegetarian`, `contains_allergens`, `menu_url` |
| `calendar.alex_school_meals_lunches` | On during a school lunch day | One all day event per school day, every course in the description |
| `binary_sensor.alex_school_meals_school_day` | On when school is open today | `closure_reason`, `next_school_day`, `next_closure`, `next_closure_reason`, `term_dates_known` |
| `sensor.alex_school_meals_cycle_week` | 1, 2 or 3 (diagnostic) | |
| `sensor.alex_school_meals_today_<course>` and `_next_school_day_<course>` | That course's dishes, e.g. "Fresh Bread, Fresh Fruit Platter, Oatie Biscuits", or "No school" | `date`, `course`, `dishes`, `vegetarian`, `contains_allergens`, `allergens` (with that option on) |

Courses follow the menu: `starter_dessert`, `meal_1`, `meal_2` and `drinks` for
primary (nursery adds `snack_am` and `snack_pm`); `starter_dessert`,
`main_courses`, `sides`, `vegetables`, `grab_and_go` and `snacks` for
secondary. Every entity carries an attribution: always check with the school.

`courses` maps each course to its dishes, as the council names them: "Meal 1",
"Meal 2", "Starter/Dessert" and "Drinks" for primary; "Main Courses", "Sides",
"Grab and Go" and "Snacks" for secondary. `vegetarian` and
`contains_allergens` list the dishes the council marks V and A. Turn on
**Named allergens** for which ones.

## Allergen watch list

When adding or changing a child you can pick allergens to watch from the UK's
14 (peanuts, tree nuts, milk and so on). The child's device then gets:

| Entity | State |
| --- | --- |
| `binary_sensor.alex_school_meals_watched_allergen_today` | On when a dish today lists a watched allergen; unknown when a dish is flagged as containing allergens but its names are not available; off otherwise |
| `binary_sensor.alex_school_meals_watched_allergen_next_school_day` | The same for the next school day |

Attributes: `date`, `watching`, `contains` (dish to the council's allergen
names) and `unknown` (dishes that could not be checked).

> **Please read.** These sensors only repeat what West Dunbartonshire Council
> publishes on its dish pages. "May contain" warnings appear on some dishes
> only (for example "May contain Sesame"), the information can change, and it
> may not match what your child is served, for example an adapted menu agreed
> with the school for a medical diet. **Off does not mean safe.** Always check
> with the school and its catering staff.

The council's own spellings vary ("Egg" and "Eggs", "Sulphite" and
"Sulphites", "Wheat" for gluten), so names are matched to the 14 by pattern.
Watching any allergen turns on reading dish pages for that child's menu.
Diagnostics downloads leave the watch list out.

## Get menu action

`wdc_school_meals.get_menu` returns a child's lunch for any date in the
current academic year. Point it at any of the child's entities:

```yaml
action: wdc_school_meals.get_menu
data:
  entity_id: sensor.alex_school_meals_today
  date: "2026-11-10"
response_variable: lunch
```

The response has `date`, `child`, `menu`, `school_day`, `closure_reason`,
`cycle_week`, `summary`, and on school days `courses`, `vegetarian`,
`contains_allergens` (and `allergens` when that option is on).

## Examples

A tile for today:

```yaml
type: tile
entity: sensor.alex_school_meals_today
name: Lunch Today
```

The week ahead:

```yaml
type: calendar
entities:
  - calendar.alex_school_meals_lunches
initial_view: listWeek
```

Every course on the next school day:

```yaml
type: markdown
content: |
  {% set s = 'sensor.alex_school_meals_next_school_day' %}
  **{{ state_attr(s, 'date') | as_datetime | as_timestamp | timestamp_custom('%A %-d %B') }}**
  {% for course, dishes in (state_attr(s, 'courses') or {}).items() %}
  - {{ course }}: {{ dishes | join(', ') }}
  {% endfor %}
```

A heads-up the evening before, so they can choose:

```yaml
triggers:
  - trigger: time
    at: "19:00:00"
conditions:
  - condition: template
    value_template: >
      {{ state_attr('sensor.alex_school_meals_next_school_day', 'date')
         == (now() + timedelta(days=1)).date() | string }}
actions:
  - action: notify.notify
    data:
      title: Lunch Tomorrow
      message: "{{ states('sensor.alex_school_meals_next_school_day') }}"
```

## How it works

- Menus: the council's menu pages, which take a `?date=` and return that week.
  Each menu runs on a three week cycle.
- Term dates: the council's term dates pages, read once a day. The menu pages
  show menus in holiday weeks too, so the term dates decide which days count.
- Children on the same menu share one fetch. A fetched week is kept for 12
  hours, so it is a few small requests a day per menu (more on the day a new
  week starts), with a clear User-Agent. Dish pages are kept on disk for a week.

## Limitations

- Schools can swap dishes on the day; those changes are not published.
- Private funded nurseries do their own food and are not listed.
- KEYS (Kilpatrick Early Years Service) links to the Kilpatrick High menu on the
  council site, which looks wrong, so it is not listed. Pick a menu instead.
- Menus exist for the current academic year only. Outside it the sensors show
  nothing.

## Troubleshooting

- A repair saying a **menu page has changed** means the council's page layout
  changed. Check for an update, or open an issue.
- A repair saying **term dates cannot be read** means every weekday shows a
  lunch until it is fixed.
- **Download diagnostics** from the integration page and attach it to issues.
  It holds the children's names and schools, nothing else personal.

## Development

```bash
scripts/test
```

Runs ruff and pytest in a throwaway uv environment pinned to Home Assistant
2026.10.4. Tests use saved council pages in `tests/fixtures/`; refresh them with
`scripts/refresh-fixtures`. Design notes are in [docs/](docs/).

## Support

This is a free side project. If it saves you a trip to the school website and you
fancy saying thanks, you can
[buy me a beer](https://buymeacoffee.com/andrewbarber). Never expected, always
appreciated.

## Licence

MIT, see [LICENSE](LICENSE). Menu content belongs to West Dunbartonshire Council.
