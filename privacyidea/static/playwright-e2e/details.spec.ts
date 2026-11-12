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
import { settle, sideways } from "./support/helpers";
import { DETAIL_PAGES, openFirstRecord } from "./support/records";
import { expectNoNewViolations } from "./support/axe";
import { SCREEN, ZOOMS } from "./support/routes";

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
