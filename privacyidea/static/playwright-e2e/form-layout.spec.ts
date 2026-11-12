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

import { expect, Page } from "@playwright/test";
import { test } from "./support/test";
import { SCREEN, ZOOMS } from "./support/routes";
import { openPage, settle } from "./support/helpers";

// Controls that belong together stay together: a form field in a table cell fills its row like its neighbours, and
// the info icon that explains a checkbox stays on the checkbox's row. Nothing is saved: a resolver type is chosen and
// a stage and an action are added to a policy that is then left.

// The resolver types whose form starts with a filled attribute mapping table.
const MAPPING_RESOLVERS = ["EntraID", "Keycloak"];

// For each form field in a cell of the mapping table: how much of the row's height, less its divider, it leaves free.
async function mappingFieldGaps(page: Page): Promise<{ column: string; gap: number }[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>(".mapping-table td mat-form-field")].map((field) => {
      const cell = field.closest("td")!;
      const divider = parseFloat(getComputedStyle(cell).borderBottomWidth) || 0;
      const column = [...cell.classList].find((c) => c.startsWith("mat-column-"))?.replace("mat-column-", "") ?? "";
      return {
        column,
        gap: cell.getBoundingClientRect().height - divider - field.getBoundingClientRect().height
      };
    })
  );
}

test.describe("attribute mapping table", () => {
  for (const type of MAPPING_RESOLVERS) {
    test(`${type} resolver: every field fills its row`, async ({ page }) => {
      await openPage(page, "users/resolvers/new");
      await page.getByRole("combobox", { name: "Type" }).click();
      await page.getByRole("option", { name: type, exact: true }).click();
      await expect(page.locator(".mapping-table td mat-form-field").first()).toBeVisible();
      await settle(page);

      const gaps = await mappingFieldGaps(page);
      expect(gaps.length, "form fields in the mapping table").toBeGreaterThan(0);
      // A select and an input in the same row end on the same line; half a pixel is rounding.
      const short = gaps.filter(({ gap }) => Math.abs(gap) > 0.5).map(({ column, gap }) => `${column}: ${gap}px`);
      expect([...new Set(short)], "fields that do not fill their row").toEqual([]);
    });
  }
});

test.describe("conditional access action", () => {
  test("the re-trigger checkbox stays beside the action select, and its hint beside it, at every zoom", async ({
    page
  }) => {
    await openPage(page, "policies/conditional-access/new");
    await page.getByRole("button", { name: "Add Stage" }).click();
    const stage = page.locator(".ca-stage-item").first();
    await expect(stage).toBeVisible();
    if ((await stage.locator(".ca-action-item").count()) === 0) {
      await stage.getByRole("button", { name: "Add Action" }).click();
    }
    const action = stage.locator(".ca-action-item").first();
    // A new action starts open; one that does not is opened.
    if (!(await action.evaluate((e) => e.classList.contains("mat-expanded")))) {
      await action.locator("mat-expansion-panel-header").click();
    }
    const checkbox = action.locator("mat-checkbox", { hasText: "Re-trigger" });
    const hint = action.getByRole("button", { name: "About re-triggering" });
    const select = action.locator("mat-form-field").first();
    await expect(checkbox).toBeVisible();
    await expect(hint).toBeVisible();

    for (const zoom of ZOOMS) {
      await page.setViewportSize({
        width: Math.round(SCREEN.width / zoom),
        height: Math.round(SCREEN.height / zoom)
      });
      await settle(page);
      const at = `${Math.round(zoom * 100)}% zoom`;
      const box = (await checkbox.boundingBox())!;
      const icon = (await hint.boundingBox())!;
      const iconMiddle = icon.y + icon.height / 2;
      expect.soft(iconMiddle, `${at}: the hint is level with its checkbox`).toBeGreaterThan(box.y);
      expect.soft(iconMiddle, `${at}: the hint is level with its checkbox`).toBeLessThan(box.y + box.height);
      expect.soft(icon.x - (box.x + box.width), `${at}: the hint follows the label, px apart`).toBeLessThanOrEqual(8);
      expect.soft(icon.x, `${at}: the hint comes after the checkbox`).toBeGreaterThanOrEqual(box.x + box.width - 1);
      const field = (await select.boundingBox())!;
      expect
        .soft(box.y, `${at}: the checkbox sits beside the action select, not below it`)
        .toBeLessThan(field.y + field.height);
    }
  });
});
