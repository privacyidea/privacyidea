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
    expect(levels.length, "the page has a heading").toBeGreaterThan(0);
    const jumps = levels.flatMap((level, i) =>
      i > 0 && level > levels[i - 1] + 1 ? [`h${levels[i - 1]} -> h${level}`] : []
    );
    expect(jumps).toEqual([]);
  });
}
