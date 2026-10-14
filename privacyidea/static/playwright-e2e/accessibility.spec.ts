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

import { test } from "./support/test";
import { ALL_PAGES } from "./support/routes";
import { openPage } from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";

// Every page, in the light and the dark theme. See support/axe.ts for the baseline.
for (const scheme of ["light", "dark"] as const) {
  test.describe(`axe, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of ALL_PAGES) {
      test(route.name, async ({ page }, testInfo) => {
        await openPage(page, route.path);
        await expectNoNewViolations(page, route.name, scheme, testInfo);
      });
    }
  });
}
