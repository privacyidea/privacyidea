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
import { ADMIN_SESSION_FILE, ADMIN_STATE_FILE, login } from "./session";

// Each run writes its results and report to a directory of its own (playwright.config.ts); the newest are kept.
const KEPT_RUNS = 5;

// Removes all but the newest KEPT_RUNS run directories under `dir`; the running one is always among them.
function pruneRuns(dir: string): void {
  if (!fs.existsSync(dir)) {
    return;
  }
  const older = fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && e.name !== process.env["E2E_RUN_ID"])
    .map((e) => path.join(dir, e.name))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  for (const run of older.slice(KEPT_RUNS - 1)) {
    fs.rmSync(run, { recursive: true, force: true });
  }
}

// Logs in once and stores the session, so every spec starts authenticated.
export default async function globalSetup(config: FullConfig): Promise<void> {
  pruneRuns(path.join(__dirname, "..", "test-results"));
  pruneRuns(path.join(__dirname, "..", "playwright-report"));

  const baseURL = config.projects[0].use.baseURL as string;
  fs.mkdirSync(path.dirname(ADMIN_STATE_FILE), { recursive: true });
  const browser = await chromium.launch();
  try {
    const session = await login(
      browser,
      baseURL,
      process.env["E2E_USER"] ?? "admin",
      process.env["E2E_PASS"] ?? "admin",
      ADMIN_STATE_FILE
    );
    // The session lives in sessionStorage, which the stored state does not hold; support/test.ts restores it.
    fs.writeFileSync(ADMIN_SESSION_FILE, session);
  } finally {
    await browser.close();
  }
}
