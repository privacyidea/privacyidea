import { expect, test } from "./support/test";
import { ALL_PAGES } from "./support/routes";
import { openPage } from "./support/helpers";

// WCAG 1.4.10 Reflow: at 320 CSS px (a 1280px window at 400% zoom) content reads without scrolling sideways. A table
// may scroll inside its own region; the page itself may not.
test.describe("reflow at 320 CSS px", () => {
  test.use({ viewport: { width: 320, height: 568 }, deviceScaleFactor: 4 });

  for (const route of ALL_PAGES) {
    test(`${route.name}: the page itself never scrolls sideways`, async ({ page }) => {
      await openPage(page, route.path);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }
});
