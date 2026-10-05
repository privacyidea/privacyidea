import { expect, test } from "./support/test";
import { ALL_PAGES } from "./support/routes";
import { openPage } from "./support/helpers";
import { focusIndicatorMisses } from "./support/focus";

// prefers-reduced-motion: a page that settles has nothing left moving. Only the progress indicators a user waits on
// and the ripple of a click may animate.
test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  for (const route of ALL_PAGES) {
    test(`${route.name}: nothing keeps animating`, async ({ page }) => {
      await openPage(page, route.path);
      await page.waitForTimeout(500);
      const moving = await page.evaluate(() =>
        document
          .getAnimations()
          .filter((a) => a.playState === "running")
          .map((a) => {
            const target = (a.effect as KeyframeEffect | null)?.target as HTMLElement | null;
            return {
              element: target,
              name: (a as CSSAnimation).animationName ?? (a as CSSTransition).transitionProperty
            };
          })
          .filter(
            ({ element }) =>
              !element?.closest(
                "mat-progress-bar, mat-progress-spinner, mat-spinner, .mat-ripple, .mdc-linear-progress"
              )
          )
          .map(
            ({ element, name }) =>
              `${element?.tagName.toLowerCase()}.${String(element?.className).split(" ")[0]}: ${name}`
          )
      );
      expect(moving).toEqual([]);
    });
  }
});

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
      expect(await focusIndicatorMisses(page)).toEqual([]);
    });
  }
});
