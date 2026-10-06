import { expect, test } from "./support/test";
import { TABLE_PAGES } from "./support/routes";
import { Page } from "@playwright/test";
import {
  applyFilter,
  emptyApi,
  expectAdminPage,
  filterInput,
  forceTheme,
  hasEmptyList,
  holdApi,
  settle
} from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";

// Opens a table page and returns the panel it shows in place of its table. Every table page has one in these states, so
// a page without it (or one that fell back to the login) fails.
async function openStatePanel(page: Page, path: string) {
  await page.goto(path);
  await expectAdminPage(page);
  const panel = page.locator(".table-state").first();
  await expect(panel, "the table-state panel").toBeVisible({ timeout: 10_000 });
  await forceTheme(page);
  return panel;
}

// The panel a table page shows in place of its table (app-table-state): while it loads, when the data could not be
// loaded, when the instance holds no data and when a filter matches nothing. Each is a state of its own for a screen reader and for contrast.
for (const scheme of ["light", "dark"] as const) {
  test.describe(`table states, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of TABLE_PAGES) {
      test(`${route.name}: loading`, async ({ page }, testInfo) => {
        test.skip(route.name === "realms", "the realm list comes from an endpoint the app shell needs");
        await holdApi(page, "loading");
        const panel = await openStatePanel(page, route.path);

        await expect(panel).toHaveAttribute("role", "status");
        await expect(panel.getByRole("progressbar", { name: /.+/ })).toBeVisible();
        await expectNoNewViolations(page, `${route.name} (loading)`, scheme, testInfo);
      });

      test(`${route.name}: error`, async ({ page }, testInfo) => {
        test.skip(route.name === "realms", "the realm list comes from an endpoint the app shell needs");
        await holdApi(page, "error");
        const panel = await openStatePanel(page, route.path);

        await expect(panel.getByRole("heading").first()).toBeVisible();
        await expect(panel.getByRole("button", { name: /.+/ }).first()).toBeVisible();
        // The failed request also raises a toast; let it finish its enter animation and announcement before looking.
        await expect(page.locator(".mat-mdc-snack-bar-container").first())
          .toBeVisible({ timeout: 3_000 })
          .catch(() => undefined);
        await settle(page);
        await expectNoNewViolations(page, `${route.name} (error)`, scheme, testInfo);
      });

      test(`${route.name}: empty`, async ({ page }, testInfo) => {
        test.skip(route.name === "realms", "the realm list comes from an endpoint the app shell needs");
        test.skip(!hasEmptyList(route.name), "no list endpoint known for this page");
        await emptyApi(page, route.name);
        const panel = await openStatePanel(page, route.path);

        await expect(panel).toHaveAttribute("role", "status");
        await expect(panel.getByRole("heading").first()).toBeVisible();
        // The call to action (create, import, ...) is only there where the page offers one.
        const action = panel.getByRole("button").or(panel.getByRole("link"));
        for (const element of await action.all()) {
          await expect(element).toHaveAccessibleName(/.+/);
        }
        await expectNoNewViolations(page, `${route.name} (empty)`, scheme, testInfo);
      });
    }
  });
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`table state, a filter that matches nothing, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });
    for (const route of TABLE_PAGES) {
      test(`${route.name}: filtered`, async ({ page }, testInfo) => {
        await page.goto(route.path, { waitUntil: "networkidle" });
        await expectAdminPage(page);
        const input = filterInput(page);
        test.skip((await input.count()) === 0, "no filter on this page");

        await applyFilter(page, "zzzzqq");
        const panel = page.locator(".table-state").first();
        await expect(panel, "the panel of a filter that matches nothing").toBeVisible({ timeout: 10_000 });
        await forceTheme(page);

        await expect(panel.getByRole("heading").first()).toBeVisible();
        await expect(panel.getByRole("button", { name: /.+/ }).first()).toBeVisible();
        await expectNoNewViolations(page, `${route.name} (filtered)`, scheme, testInfo);
      });
    }
  });
}
