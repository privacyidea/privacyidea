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

import { Browser, BrowserContext, Page, TestInfo, test as base } from "@playwright/test";
import * as fs from "fs";
import { ADMIN_SESSION_FILE, restoreSession } from "./session";

export { expect } from "@playwright/test";

const adminSession = () => fs.readFileSync(ADMIN_SESSION_FILE, "utf8");

export const test = base.extend({
  context: async ({ context }, use) => {
    await restoreSession(context, adminSession());
    await use(context);
  }
});

// A logged-in context outside the per-test fixtures, for a describe block whose tests share one loaded page (see
// pages.spec.ts). It takes the settings of the running project (playwright.config.ts) over.
export async function newAdminContext(browser: Browser, testInfo: TestInfo): Promise<BrowserContext> {
  const { baseURL, ignoreHTTPSErrors, storageState, reducedMotion, viewport, colorScheme } = testInfo.project.use;
  const context = await browser.newContext({
    baseURL,
    ignoreHTTPSErrors,
    storageState,
    reducedMotion,
    viewport,
    colorScheme
  });
  await restoreSession(context, adminSession());
  return context;
}

// For a describe block whose tests share one page outside the fixtures, which Playwright's own failure screenshot
// and trace do not cover: a failed test gets the page's address and a screenshot of it attached.
export function attachPageOnFailure(page: () => Page | undefined): void {
  test.afterEach(async ({}, testInfo) => {
    const current = page();
    if (!current || testInfo.status === testInfo.expectedStatus) {
      return;
    }
    await testInfo.attach("url", { body: current.url(), contentType: "text/plain" });
    await testInfo.attach("page", {
      body: await current.screenshot().catch(() => Buffer.alloc(0)),
      contentType: "image/png"
    });
  });
}
