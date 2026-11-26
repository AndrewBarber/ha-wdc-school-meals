# WDC school meals: what the council publishes

Researched 28 October 2026 against west-dunbarton.gov.uk (read-only, about 120
page requests, spaced out).

## Menus

Five menu pages under `/schools-and-learning/schools/school-meals/`. All five
use the same Umbraco template (`page-schoolMenuFolderPage`).

| Menu | Page | Courses per day | Price |
| --- | --- | --- | --- |
| Nursery | `nursery-menus` | Starter/Dessert, Meal 1, Meal 2, Drinks, Snack AM, Snack PM | n/a |
| Primary | `primary-menus` | Starter/Dessert, Meal 1, Meal 2, Drinks | £3.35 |
| Secondary | `secondary-menus` | Starter/Dessert, Main Courses, Sides, Vegetables, Grab and Go, Snacks | £3.35 |
| Kilpatrick Primary | `kilpatrick-primary-school` | as Primary, different dishes | £3.04 |
| Kilpatrick High | `kilpatrick-high-school` | as Secondary, different dishes | £3.04 |

- Each menu runs on a **three week cycle** (`Primary Week 1` to `3`). Each cycle
  week also has its own page (`primary-menus/primary-week-2`) and a one page
  PDF under `/media/...`.
- The menu page shows "This weeks menu" with the cycle week and a Monday to
  Saturday range in the heading: `Primary Week 3` / `26th - 31st October 2026`.
- **`?date=DD-MM-YYYY` works on every menu page** and returns the week that
  holds that date. This gives next week, or any week, from one request.
  - Covers the current academic year only: 17 Aug 2026 to 3 Jul 2027 returned
    menus; 11 Aug 2025, 1 Jun 2026 and 5 Jul 2027 return "No Menu for this
    date" with no tables.
  - The CMS rotates the cycle through holidays (12 Oct 2026, a holiday week,
    shows Week 1; Christmas weeks show menus). So **the page does not know about
    holidays**; term dates have to come from elsewhere.
  - The cycle does not restart each term: Week 2 on 17 Aug, then one step per
    calendar week. Easy to compute, but `?date` is the safer source.

## HTML structure (good for a parser)

- One `<table class="school-menu-table school-menu-table-{primary|secondary|nursery}">`
  per day, `<caption>` "Primary Week 3 Monday".
- One row per course: `<th class="school-menu-item-heading school-menu-{type}-menuitemN-heading">`
  then `<td>` with one `<div class="menu-item-entry">` per dish.
- Each dish: `<a href=".../school-meals/meals/{category}/{slug}">Name</a>` plus
  `<sup title="Suitable for vegetarians">V</sup>` and
  `<sup title="Contains allergens">A</sup>`.
- Course slot numbers (menuitem1 to 7) are stable per menu type, headings are
  plain text. A table based parser replaces today's line splitting.
- No JSON, no feed, no API (Umbraco delivery API returns 404; `/umbraco/` is
  disallowed in `robots.txt`). Responses are `CONFIG_NOCACHE` via Azure Front
  Door.

## Dish pages

132 dish pages in the sitemap (`main` 67, `side-dish` 25, `starter` 13,
`dessert` 13, `grab-go-highschools` 8, `early-year-snack` 4, `drink` 2). Each
has:

- Vegetarian flag
- **Allergens** (named, for example "Gluten, Wheat, Milk")
- Ingredients with the allergen per ingredient
- Servings by population group (Primary 7 to 10, Secondary 11 to 18)

## Schools: menus differ by stage, not by school

Every school page has a "Menu information" link. Checked all 41 schools and 41
nursery pages:

| Schools | Menu |
| --- | --- |
| 32 mainstream primaries, plus Cunard School | Primary |
| 5 high schools (Clydebank High, Dumbarton Academy, Our Lady and St Patrick's, St Peter the Apostle, Vale of Leven Academy) | Secondary |
| Kilpatrick Schools (Clydebank) | Kilpatrick High link only; the site also has Kilpatrick Primary |
| Riverside School | Kilpatrick High |
| Choices School | Links to both Kilpatrick High and Secondary |
| 29 council nurseries and ELCCs | Nursery |
| KEYS (Kilpatrick Early Years Service) | Links to Kilpatrick High, which looks like a mistake |
| 11 private funded providers | None (they do their own food) |

- Kilpatrick is confirmed ASN: "complex additional support needs at primary
  and secondary age" (Specialist Educational Settings page). Riverside is ASN
  at secondary age. Treat Kilpatrick Primary and Kilpatrick High as their own
  menus.
- No per school differences are published. The secondary page says each high
  school picks at least two Grab and Go items a day, and schools may make
  substitutions, but neither is online.

## Term dates

- `/schools-and-learning/schools/term-dates/term-date-202627` and
  `term-dates-202728`: HTML text only, no ICS or PDF.
- Lines like "Half-term - October Break: Monday 12 October 2026 - Friday 16
  October 2026 (inclusive)", "In-service Day: Monday 9 November 2026*",
  "Schools close at 2.30 p.m. on Friday 18 December 2026". Parseable with care.
- Same dates for every council school. 2026/27 and 2027/28 are both published.

## Other pages (not menus)

- Early Start Clubs (breakfast): fees only, no menu.
- Medically prescribed diets, adapted menus (vegetarian, vegan, halal on
  request): text only.

## What an integration could support

| Feature | Source | Effort |
| --- | --- | --- |
| All three stages: Nursery, Primary, Secondary | The three stage menu pages | Low |
| ASN exceptions as their own menus: Kilpatrick Primary, Kilpatrick High (Kilpatrick Schools, Riverside); ask Choices School which one | The two Kilpatrick pages | Low |
| Pick a school by name, map to its menu | Static school list, from the school pages | Low |
| This week's menu, any of the five menus | Menu page | Low |
| Today and next school day | Menu page plus `?date` for next week | Low |
| Cycle week number | Heading | Low |
| Vegetarian and "contains allergens" flags per dish | `<sup>` tags | Low |
| Calendar of lunches (this and next week, more on demand) | `?date` | Medium |
| School holidays and in-service days, so no menu on closed days | Term dates pages | Medium, fragile text |
| Named allergens and ingredients per dish | Dish pages, cached | Medium |
| A "get menu for date" action for automations and assistants | `?date` | Low once the parser exists |
| Prices | Page text | Low, low value |
| Per school substitutions | Not published | Not possible |
