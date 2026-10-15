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

import { Browser, BrowserContext, test as base } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { BASE_URL } from "./env";

export { expect } from "@playwright/test";

const SESSION_FILE = path.join(__dirname, "..", ".auth", "session.json");

// The WebUI keeps its session in sessionStorage, which a stored browser state does not carry over. This
// restores what global-setup saved after login, before any page script runs.
async function restoreSession(context: BrowserContext): Promise<void> {
  const session = fs.readFileSync(SESSION_FILE, "utf8");
  await context.addInitScript((entries: string) => {
    if (location.origin === "null") {
      return;
    }
    for (const [key, value] of Object.entries(JSON.parse(entries) as Record<string, string>)) {
      if (sessionStorage.getItem(key) === null) {
        sessionStorage.setItem(key, value);
      }
    }
  }, session);
}

export const test = base.extend({
  context: async ({ context }, use) => {
    await restoreSession(context);
    await use(context);
  }
});

// A logged-in context outside the per-test fixtures, for a describe block whose tests share one loaded page (see
// pages.spec.ts). It takes the project's settings over by hand: reduced motion, the 1920x1080 screen, the base URL.
export async function newAdminContext(browser: Browser): Promise<BrowserContext> {
  const context = await browser.newContext({
    baseURL: BASE_URL,
    ignoreHTTPSErrors: true,
    storageState: path.join(__dirname, "..", ".auth", "admin.json"),
    reducedMotion: "reduce",
    viewport: { width: 1920, height: 1080 }
  });
  await restoreSession(context);
  return context;
}
