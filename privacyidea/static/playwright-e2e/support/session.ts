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

import { Browser, BrowserContext } from "@playwright/test";
import * as path from "path";

// What global-setup saves after the administrator's login: the browser state and the session.
export const ADMIN_STATE_FILE = path.join(__dirname, "..", ".auth", "admin.json");
export const ADMIN_SESSION_FILE = path.join(__dirname, "..", ".auth", "session.json");

// Logs `user` in through the login form and returns the session the WebUI keeps in sessionStorage, as JSON. With
// `stateFile`, the browser state (cookies, localStorage) is saved there as well.
export async function login(
  browser: Browser,
  baseURL: string,
  user: string,
  password: string,
  stateFile?: string
): Promise<string> {
  const context = await browser.newContext({ baseURL, ignoreHTTPSErrors: true });
  try {
    const page = await context.newPage();
    await page.goto("login");
    await page.fill("#username", user);
    await page.fill("#password", password);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 20_000 });
    if (stateFile) {
      await context.storageState({ path: stateFile });
    }
    return await page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage))));
  } finally {
    await context.close();
  }
}

// The WebUI keeps its session in sessionStorage, which a stored browser state does not carry over. This puts the
// entries `login` returned back before any page script runs.
export async function restoreSession(context: BrowserContext, entries: string): Promise<void> {
  await context.addInitScript((entries: string) => {
    if (location.origin === "null") {
      return;
    }
    for (const [key, value] of Object.entries(JSON.parse(entries) as Record<string, string>)) {
      if (sessionStorage.getItem(key) === null) {
        sessionStorage.setItem(key, value);
      }
    }
  }, entries);
}
