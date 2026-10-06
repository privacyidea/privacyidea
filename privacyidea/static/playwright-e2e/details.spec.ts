import { Browser, BrowserContext, Page } from "@playwright/test";
import { expect, newAdminContext, test } from "./support/test";
import { forceTheme, openPage, settle } from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";
import { SCREEN, ZOOMS } from "./support/routes";

// The detail and edit pages need an existing record: each is reached the way a user gets there, from the first row
// of its list. A list without rows skips its test.
const DETAIL_PAGES: { name: string; list: string }[] = [
  { name: "token details", list: "tokens" },
  { name: "container details", list: "containers" },
  { name: "container template details", list: "containers/templates" },
  { name: "user details", list: "users" },
  { name: "resolver details", list: "users/resolvers" },
  { name: "policy details", list: "policies" },
  { name: "conditional access details", list: "policies/conditional-access" },
  { name: "api client details", list: "policies/api-clients" },
  { name: "event details", list: "events" },
  { name: "machine details", list: "configuration/machines" },
  { name: "machine resolver details", list: "configuration/machine_resolver" },
  { name: "periodic task details", list: "configuration/periodic-tasks" },
  { name: "smtp server details", list: "external-services/smtp" },
  { name: "radius server details", list: "external-services/radius" },
  { name: "sms gateway details", list: "external-services/sms" },
  { name: "privacyidea server details", list: "external-services/privacyidea" }
];

// The address of a record's page: the detail (or edit) route of its list.
const RECORD_URL = /\/(details|edit)\//;

// Opens the first row's record the way a user does: through the link or button in the row's name column, else the first
// one in the row. Returns false when the list has no rows; a click that leads nowhere fails the test.
async function openFirstRecord(page: Page, list: string): Promise<boolean> {
  await openPage(page, list);
  const row = page.locator("tr.mat-mdc-row, mat-row, .event-handler-row, .mat-mdc-row").first();
  if ((await row.count()) === 0) {
    return false;
  }
  const control = "a, button:not(.copy-button):not(.sort-button):not(.filter-button)";
  const primary = row.locator(
    "td.mat-column-serial, td.mat-column-name, td.mat-column-username, td.mat-column-policyname, td.mat-column-container_serial"
  );
  const inName = primary.locator(control).first();
  const link = (await inName.count()) > 0 ? inName : row.locator(control).first();
  await ((await link.count()) > 0 ? link : row).click({ position: { x: 20, y: 10 } });
  await expect(page, `the first row of ${list} opens its record`).toHaveURL(RECORD_URL, { timeout: 10_000 });
  await page.waitForLoadState("networkidle");
  await settle(page);
  await forceTheme(page);
  return true;
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`details, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const detail of DETAIL_PAGES) {
      test(`${detail.name}: axe`, async ({ page }, testInfo) => {
        test.skip(!(await openFirstRecord(page, detail.list)), "no record to open");
        await expectNoNewViolations(page, detail.name, scheme, testInfo);
      });
    }
  });
}

// One load per record for the rest: structure, the keyboard and the layout at each browser zoom (the viewport is
// resized rather than the page reloaded).
for (const detail of DETAIL_PAGES) {
  test.describe(`${detail.name}: structure, keyboard and zoom`, () => {
    test.describe.configure({ mode: "default" });
    let context: BrowserContext;
    let page: Page;
    let opened = false;

    test.beforeAll(async ({ browser }: { browser: Browser }) => {
      context = await newAdminContext(browser);
      page = await context.newPage();
      opened = await openFirstRecord(page, detail.list);
    });

    // The page is not a fixture, so Playwright's own failure screenshot and trace do not cover it.
    test.afterEach(async ({}, testInfo) => {
      if (testInfo.status !== testInfo.expectedStatus) {
        await testInfo.attach("url", { body: page.url(), contentType: "text/plain" });
        await testInfo.attach("page", {
          body: await page.screenshot().catch(() => Buffer.alloc(0)),
          contentType: "image/png"
        });
      }
    });

    test.afterAll(async () => {
      await context?.close();
    });

    test("landmarks and title", async () => {
      test.skip(!opened, "no record to open");
      expect(await page.locator("main, [role='main']").count()).toBe(1);
      expect((await page.title()).trim()).not.toBe("");
    });

    test("the page itself never scrolls sideways at any zoom", async () => {
      test.skip(!opened, "no record to open");
      for (const zoom of [...ZOOMS].reverse()) {
        await page.setViewportSize({
          width: Math.round(SCREEN.width / zoom),
          height: Math.round(SCREEN.height / zoom)
        });
        await settle(page);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        expect.soft(overflow, `${Math.round(zoom * 100)}% zoom`).toBeLessThanOrEqual(1);
      }
      await page.setViewportSize({ width: SCREEN.width, height: SCREEN.height });
      await settle(page);
    });

    test("Tab reaches the controls and none of them is invisible", async () => {
      test.skip(!opened, "no record to open");
      const seen: string[] = [];
      const invisible: string[] = [];
      for (let i = 0; i < 40; i++) {
        await page.keyboard.press("Tab");
        const info = await page.evaluate(() => {
          const e = document.activeElement as HTMLElement | null;
          if (!e || e === document.body) {
            return null;
          }
          const r = e.getBoundingClientRect();
          return {
            id: e.tagName.toLowerCase() + "." + String(e.className).split(" ")[0],
            visible: r.width > 0 && r.height > 0
          };
        });
        if (!info) {
          // A page that re-renders as its data arrives can drop focus to the body for a moment; Tab goes on.
          continue;
        }
        seen.push(info.id);
        if (!info.visible) {
          invisible.push(info.id);
        }
      }
      expect(invisible).toEqual([]);
      expect(seen.length).toBeGreaterThan(3);
    });
  });
}
