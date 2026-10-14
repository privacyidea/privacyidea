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
