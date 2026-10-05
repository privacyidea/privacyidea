import { expect, test } from "./support/test";
import { TABLE_PAGES } from "./support/routes";
import { filterInput, holdApi } from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";

// The panel a table page shows in place of its table (app-table-state): while it loads, when the data could not be
// loaded, and when a filter matches nothing. Each is a state of its own for a screen reader and for contrast.
for (const scheme of ["light", "dark"] as const) {
  test.describe(`table states, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of TABLE_PAGES) {
      test(`${route.name}: loading`, async ({ page }, testInfo) => {
        test.skip(route.name === "realms", "the realm list comes from an endpoint the app shell needs");
        await holdApi(page, "loading");
        await page.goto(route.path);
        const panel = page.locator(".table-state").first();
        test.skip(
          !(await panel.waitFor({ timeout: 8_000 }).then(
            () => true,
            () => false
          )),
          "page has no table state panel"
        );

        await expect(panel).toHaveAttribute("role", "status");
        await expect(panel.getByRole("progressbar", { name: /.+/ })).toBeVisible();
        await expectNoNewViolations(page, `${route.name} (loading)`, scheme, testInfo);
      });

      test(`${route.name}: error`, async ({ page }, testInfo) => {
        test.skip(route.name === "realms", "the realm list comes from an endpoint the app shell needs");
        await holdApi(page, "error");
        await page.goto(route.path);
        const panel = page.locator(".table-state").first();
        test.skip(
          !(await panel.waitFor({ timeout: 8_000 }).then(
            () => true,
            () => false
          )),
          "page has no table state panel"
        );

        await expect(panel.getByRole("heading").first()).toBeVisible();
        await expect(panel.getByRole("button", { name: /.+/ }).first()).toBeVisible();
        // The failed request also raises a toast; let it finish its enter animation and announcement before looking.
        await page.waitForTimeout(1500);
        await expectNoNewViolations(page, `${route.name} (error)`, scheme, testInfo);
      });
    }
  });
}

test.describe("table state, a filter that matches nothing", () => {
  for (const route of TABLE_PAGES) {
    test(`${route.name}: filtered`, async ({ page }, testInfo) => {
      await page.goto(route.path, { waitUntil: "networkidle" });
      const input = filterInput(page);
      test.skip((await input.count()) === 0, "no filter on this page");

      await input.fill("zzzzqq");
      const panel = page.locator(".table-state").first();
      test.skip(
        !(await panel.waitFor({ timeout: 4_000 }).then(
          () => true,
          () => false
        )),
        "this table shows no panel for it"
      );

      await expect(panel.getByRole("heading").first()).toBeVisible();
      await expect(panel.getByRole("button", { name: /.+/ }).first()).toBeVisible();
      await expectNoNewViolations(page, `${route.name} (filtered)`, "light", testInfo);
    });
  }
});
