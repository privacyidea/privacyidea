/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { Browser, BrowserContext, Page } from "@playwright/test";
import { attachPageOnFailure, expect, newAdminContext, test } from "./support/test";
import { openPage, settle, settleContent, sideways } from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";
import { SCREEN, ZOOMS } from "./support/routes";

// The detail and edit pages need an existing record: each is reached the way a user gets there, from the first row
// of its list, through the control in the column that names the record. A list without rows skips its test.
interface DetailPage {
  name: string;
  list: string;
  column: string;
}

const DETAIL_PAGES: DetailPage[] = [
  { name: "token details", list: "tokens", column: "serial" },
  { name: "container details", list: "containers", column: "serial" },
  { name: "container template details", list: "containers/templates", column: "name" },
  { name: "user details", list: "users", column: "username" },
  { name: "resolver details", list: "users/resolvers", column: "resolvername" },
  { name: "policy details", list: "policies", column: "name" },
  { name: "conditional access details", list: "policies/conditional-access", column: "name" },
  { name: "api client details", list: "policies/api-clients", column: "display_name" },
  { name: "event details", list: "events", column: "name" },
  { name: "machine details", list: "configuration/machines", column: "hostname" },
  { name: "machine resolver details", list: "configuration/machine_resolver", column: "resolvername" },
  { name: "periodic task details", list: "configuration/periodic-tasks", column: "name" },
  { name: "smtp server details", list: "external-services/smtp", column: "identifier" },
  { name: "radius server details", list: "external-services/radius", column: "identifier" },
  { name: "sms gateway details", list: "external-services/sms", column: "name" },
  { name: "privacyidea server details", list: "external-services/privacyidea", column: "identifier" }
];

// The address of a record's page: the detail (or edit) route of its list.
const RECORD_URL = /\/(details|edit)\//;

// Opens the first row's record the way a user does: through the link or button in the row's name cell. Returns why
// that is not possible (no rows, or a name without a control, as on a list the user may only read); a click that
// leads nowhere fails the test.
async function openFirstRecord(page: Page, detail: DetailPage): Promise<string | undefined> {
  await openPage(page, detail.list);
  const row = page.locator("tr.mat-mdc-row, mat-row, .event-handler-row, .mat-mdc-row").first();
  if ((await row.count()) === 0) {
    return "no record to open";
  }
  const link = row
    .locator(`td.mat-column-${detail.column}`)
    .locator("a, button:not(.copy-button):not(.sort-button):not(.filter-button)")
    .first();
  if ((await link.count()) === 0) {
    return "the record's name opens nothing here";
  }
  await link.click();
  await expect(page, `the first row of ${detail.list} opens its record`).toHaveURL(RECORD_URL, { timeout: 10_000 });
  await page.waitForLoadState("networkidle");
  await settleContent(page);
  return undefined;
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`details, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const detail of DETAIL_PAGES) {
      test(`${detail.name}: axe`, async ({ page }, testInfo) => {
        const notOpened = await openFirstRecord(page, detail);
        test.skip(!!notOpened, notOpened);
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
    let notOpened: string | undefined;

    test.beforeAll(async ({ browser }: { browser: Browser }, testInfo) => {
      context = await newAdminContext(browser, testInfo);
      page = await context.newPage();
      notOpened = await openFirstRecord(page, detail);
    });

    attachPageOnFailure(() => page);

    test.afterAll(async () => {
      await context?.close();
    });

    test("landmarks and title", async () => {
      test.skip(!!notOpened, notOpened);
      expect(await page.locator("main, [role='main']").count()).toBe(1);
      expect((await page.title()).trim()).not.toBe("");
    });

    test("the page itself never scrolls sideways at any zoom", async () => {
      test.skip(!!notOpened, notOpened);
      for (const zoom of [...ZOOMS].reverse()) {
        await page.setViewportSize({
          width: Math.round(SCREEN.width / zoom),
          height: Math.round(SCREEN.height / zoom)
        });
        await settle(page);
        expect.soft(await sideways(page), `${Math.round(zoom * 100)}% zoom`).toBeLessThanOrEqual(1);
      }
      await page.setViewportSize({ width: SCREEN.width, height: SCREEN.height });
      await settle(page);
    });

    test("Tab reaches the controls and none of them is invisible", async () => {
      test.skip(!!notOpened, notOpened);
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
