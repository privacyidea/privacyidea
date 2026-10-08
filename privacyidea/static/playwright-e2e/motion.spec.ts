import { expect, test } from "./support/test";
import { ALL_PAGES } from "./support/routes";
import { openPage } from "./support/helpers";
import { focusIndicatorMisses } from "./support/focus";

// Forced colors (Windows High Contrast): backgrounds are replaced by system colors, so a control's focus must still
// show as an outline or border.
test.describe("forced colors", () => {
  test.use({ forcedColors: "active" });

  for (const route of ALL_PAGES.filter((r) =>
    ["tokens", "policies", "users", "dashboard", "policy create"].includes(r.name)
  )) {
    test(`${route.name}: a focused control is still marked`, async ({ page }) => {
      await openPage(page, route.path);
      expect(await page.evaluate(() => matchMedia("(forced-colors: active)").matches)).toBe(true);
      const { misses, checked } = await focusIndicatorMisses(page);
      expect(checked, "controls of the page content checked").toBeGreaterThanOrEqual(3);
      expect(misses).toEqual([]);
    });
  }
});
