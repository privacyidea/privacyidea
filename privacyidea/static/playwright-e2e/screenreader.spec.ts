import { expect, test } from "./support/test";
import { ALL_PAGES } from "./support/routes";
import { openPage } from "./support/helpers";

// What a screen reader is given: the accessibility tree of the page as Playwright reads it. A control without a name
// is announced as just "button", and a heading level that skips one breaks the outline.
const NAMED_ROLES =
  "button|link|checkbox|radio|switch|textbox|combobox|slider|menuitem|tab|option|searchbox|spinbutton";
const UNNAMED = new RegExp(`^\\s*- (${NAMED_ROLES})(?: \\[[^\\]]*\\])*:?$`, "gm");
const HEADING = /^\s*- heading "[^"]*" \[level=(\d)\]/gm;

for (const route of ALL_PAGES) {
  test(`${route.name}: every control is announced with a name`, async ({ page }) => {
    await openPage(page, route.path);
    const snapshot = await page.locator("body").ariaSnapshot();
    expect(snapshot.match(UNNAMED) ?? []).toEqual([]);
  });

  test(`${route.name}: the headings form an outline`, async ({ page }) => {
    await openPage(page, route.path);
    const snapshot = await page.locator("body").ariaSnapshot();
    const levels = [...snapshot.matchAll(HEADING)].map((m) => Number(m[1]));
    // The page is named by one h1; the headings the page draws itself follow, each at most one level below the last.
    expect(levels.filter((l) => l === 1).length, "one h1").toBe(1);
    expect(levels[0], "the h1 comes first").toBe(1);
    const own = levels.slice(1);
    const jumps = own.flatMap((level, i) => (i > 0 && level > own[i - 1] + 1 ? [`h${own[i - 1]} -> h${level}`] : []));
    expect(jumps).toEqual([]);
  });
}
