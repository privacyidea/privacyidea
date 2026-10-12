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

import { chromium, FullConfig } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

// Logs in once and stores the session, so every spec starts authenticated.
export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0].use.baseURL as string;
  const file = path.join(__dirname, "..", ".auth", "admin.json");
  fs.mkdirSync(path.dirname(file), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL, ignoreHTTPSErrors: true });
  const page = await context.newPage();
  await page.goto("login");
  await page.fill("#username", process.env["E2E_USER"] ?? "admin");
  await page.fill("#password", process.env["E2E_PASS"] ?? "admin");
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 20_000 });
  await context.storageState({ path: file });
  // The session lives in sessionStorage, which storageState does not save; support/test.ts restores it.
  const session = await page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage))));
  fs.writeFileSync(path.join(path.dirname(file), "session.json"), session);
  await browser.close();
}
