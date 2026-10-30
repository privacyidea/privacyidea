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

import { expect, test } from "./support/test";
import { TABLE_PAGES } from "./support/routes";
import {
  applyFilter,
  expectTableOrState,
  filterInput,
  measureTable,
  noMatchFilter,
  openPage,
  setSticky,
  settle
} from "./support/helpers";

test.describe("table width stays put", () => {
  for (const route of TABLE_PAGES) {
    test(`${route.name}: filtering and the sticky header do not resize the table or its card`, async ({ page }) => {
      await openPage(page, route.path);
      test.skip(!(await expectTableOrState(page)), "the list is empty, the page shows its empty state");
      const input = filterInput(page);
      test.skip((await input.count()) === 0, "no filter on this page");

      const rest = await measureTable(page);
      const states: [string, Awaited<ReturnType<typeof measureTable>>][] = [];

      await setSticky(page, true);
      states.push(["sticky", await measureTable(page)]);
      await setSticky(page, false);

      // Each filter is measured once the table shows its outcome: the panel of a filter that matches nothing, then the
      // rows again. The server-side filters answer after a pause and a request, so an idle network says nothing yet.
      const outcomes = [
        { filter: noMatchFilter(route.name), shown: page.locator(".table-scroll-region .table-state") },
        { filter: "", shown: page.locator(".table-scroll-region tr.mat-mdc-row:not(:has(.table-state))") }
      ];
      for (const { filter, shown } of outcomes) {
        await applyFilter(page, filter);
        await expect(shown.first(), `the outcome of the filter "${filter}"`).toBeVisible();
        await settle(page);
        states.push([`filter "${filter}"`, await measureTable(page)]);
        await setSticky(page, true);
        states.push([`filter "${filter}" + sticky`, await measureTable(page)]);
        await setSticky(page, false);
      }

      for (const [label, box] of states) {
        expect.soft({ card: box.card, table: box.table }, label).toEqual({ card: rest.card, table: rest.table });
      }
    });
  }
});

test.describe("sticky header", () => {
  test.use({ viewport: { width: 1920, height: 560 } });

  for (const route of TABLE_PAGES) {
    test(`${route.name}: the header stays at the top of the scroll region`, async ({ page }) => {
      await openPage(page, route.path);
      test.skip(!(await expectTableOrState(page)), "the list is empty, the page shows its empty state");
      const region = page.locator(".table-scroll-region").first();
      const scrollable = await region.evaluate((r) => r.scrollHeight - r.clientHeight > 80);
      test.skip(!scrollable, "table too short to scroll here");

      await region.evaluate((r) => (r.scrollTop = 60));
      await settle(page);
      const gap = await page.evaluate(() => {
        const r = document.querySelector(".table-scroll-region")!.getBoundingClientRect();
        const h = document.querySelector("th")!.getBoundingClientRect();
        return Math.abs(h.top - r.top);
      });
      // The region's own 1px top border sits above the header.
      expect(gap).toBeLessThanOrEqual(2);
    });
  }
});
