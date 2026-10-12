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

import { test as base } from "@playwright/test";
import { BASE_URL } from "./env";

export { expect } from "@playwright/test";

// A regular (self-service) user, for the pages an administrator never sees. Set E2E_SELF_USER and E2E_SELF_PASS;
// without them the self-service specs skip.
export const SELF_USER = process.env["E2E_SELF_USER"];
export const SELF_PASS = process.env["E2E_SELF_PASS"];

// Logs the self-service user in once per worker and restores that session before any page script runs.
export const selfTest = base.extend<object, { selfSession: string }>({
  selfSession: [
    async ({ browser }, use) => {
      if (!SELF_USER || !SELF_PASS) {
        await use("");
        return;
      }
      const context = await browser.newContext({
        ignoreHTTPSErrors: true,
        baseURL: BASE_URL
      });
      const page = await context.newPage();
      await page.goto("login");
      await page.fill("#username", SELF_USER);
      await page.fill("#password", SELF_PASS);
      await page.click('button[type="submit"]');
      await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 20_000 });
      const session = await page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage))));
      await context.close();
      await use(session);
    },
    { scope: "worker" }
  ],
  // Takes the test's colour scheme, motion preference and screen over, which a context of its own would not.
  context: async ({ browser, selfSession, colorScheme, reducedMotion, viewport }, use) => {
    const context = await browser.newContext({
      ignoreHTTPSErrors: true,
      baseURL: BASE_URL,
      colorScheme,
      reducedMotion,
      viewport
    });
    if (selfSession) {
      await context.addInitScript((entries: string) => {
        if (location.origin === "null") {
          return;
        }
        for (const [key, value] of Object.entries(JSON.parse(entries) as Record<string, string>)) {
          if (sessionStorage.getItem(key) === null) {
            sessionStorage.setItem(key, value);
          }
        }
      }, selfSession);
    }
    await use(context);
    await context.close();
  },
  page: async ({ context }, use) => {
    await use(await context.newPage());
  }
});
