# Changelog

## 0.2.0 (26 November 2026)

First release. 0.1.0 was never published, so this one has everything below.

- A sensor per course (starter/dessert, each meal with its sides, drinks and so on), today and on the next school day.
- Disclaimer on the setup screen, in the README and as each entity's attribution: always check with the school.
- Fewer requests to the council site: fetched menu weeks are kept for 12 hours and reused by refreshes.
- Optional named allergens for each dish, from the council's dish pages, kept for a week.
- `wdc_school_meals.get_menu` action: a child's lunch on any date, as response data.
- Allergen watch list per child: two sensors flag a day whose menu lists a watched allergen (unknown when it cannot be checked).

## 0.1.0 (not released)

- All five council menus: Nursery, Primary, Secondary, Kilpatrick Primary, Kilpatrick High.
- Pick a child's school by name; one device per child, as many children as you like.
- Today and next school day sensors, a lunch calendar, a school day sensor and the cycle week.
- Holidays and in-service days from the council's term dates.
- Repairs when the council's pages change, and a diagnostics download.
