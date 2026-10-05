import { expect, Page } from "@playwright/test";
import { test } from "./support/test";
import { openPage } from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";
import { SCREEN } from "./support/routes";

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

// Opens the first row's record. Returns false when the list is empty or the click led nowhere.
async function openFirstRecord(page: Page, list: string): Promise<boolean> {
  await openPage(page, list);
  const row = page.locator("tr.mat-mdc-row, mat-row, .event-handler-row, .mat-mdc-row").first();
  if ((await row.count()) === 0) {
    return false;
  }
  const start = page.url();
  const link = row.locator("a, button:not(.copy-button):not(.sort-button):not(.filter-button)").first();
  await ((await link.count()) > 0 ? link : row).click({ position: { x: 20, y: 10 } });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(500);
  return page.url() !== start;
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

test.describe("details, structure and keyboard", () => {
  for (const detail of DETAIL_PAGES) {
    test(`${detail.name}: landmarks, title and Tab order`, async ({ page }) => {
      test.skip(!(await openFirstRecord(page, detail.list)), "no record to open");

      expect(await page.locator("main, [role='main']").count()).toBe(1);
      expect((await page.title()).trim()).not.toBe("");

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
          break;
        }
        seen.push(info.id);
        if (!info.visible) {
          invisible.push(info.id);
        }
      }
      expect(invisible).toEqual([]);
      expect(seen.length).toBeGreaterThan(3);
    });
  }
});

for (const zoom of [1, 1.5, 2] as const) {
  test.describe(`details at ${Math.round(zoom * 100)}% zoom`, () => {
    test.use({
      viewport: { width: Math.round(SCREEN.width / zoom), height: Math.round(SCREEN.height / zoom) },
      deviceScaleFactor: zoom
    });

    for (const detail of DETAIL_PAGES) {
      test(`${detail.name}: the page itself never scrolls sideways`, async ({ page }) => {
        test.skip(!(await openFirstRecord(page, detail.list)), "no record to open");
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        expect(overflow).toBeLessThanOrEqual(1);
      });
    }
  });
}
