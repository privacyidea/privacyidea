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

import { expect, selfTest as test, SELF_PASS, SELF_USER } from "./support/self-service";
import { expectNoNewViolations } from "./support/axe";
import { settleContent, sideways } from "./support/helpers";
import { Page } from "@playwright/test";

// The pages of the self-service user. Needs E2E_SELF_USER / E2E_SELF_PASS (see support/self-service.ts).
const SELF_PAGES = [
  { name: "self tokens", path: "tokens" },
  { name: "self token enrollment", path: "tokens/enrollment" },
  { name: "self assign token", path: "tokens/assign-token" },
  { name: "self containers", path: "containers" },
  { name: "self container create", path: "containers/create" },
  { name: "self user", path: "users" },
  { name: "self audit", path: "logs/audit" },
  { name: "self authentication log", path: "logs/authentication-log" },
  { name: "self news", path: "news" }
];

test.use({ reducedMotion: "reduce", viewport: { width: 1920, height: 1080 } });

test.beforeEach(() => {
  test.skip(!SELF_USER || !SELF_PASS, "E2E_SELF_USER and E2E_SELF_PASS are not set");
});

async function open(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "networkidle" });
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page).toHaveURL(new RegExp(`${path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/?$`));
  await settleContent(page);
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`self-service, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of SELF_PAGES) {
      test(`${route.name}: axe`, async ({ page }, testInfo) => {
        await open(page, route.path);
        await expectNoNewViolations(page, route.name, scheme, testInfo);
      });
    }
  });
}

test.describe("self-service, structure and layout", () => {
  for (const route of SELF_PAGES) {
    test(`${route.name}: landmarks, title and no sideways page scroll`, async ({ page }) => {
      await open(page, route.path);
      expect(await page.locator("main, [role='main']").count()).toBe(1);
      expect((await page.title()).trim()).not.toBe("");
      expect(await sideways(page), "the page itself scrolls sideways by").toBeLessThanOrEqual(1);
    });
  }
});
