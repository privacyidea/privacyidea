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

import { TestType } from "@playwright/test";

// Failures the WebUI has today, by check. A listed test runs and is expected to fail (test.fail): it stays
// visible in every report, a new failure elsewhere still breaks the build, and once the page is fixed the
// test reports "expected to fail, but passed" - the cue to delete its entry here.
type Known = Record<string, { reason: string; pages: string[] | "all" }>;

export const KNOWN: Known = {};

// Marks the running test as an expected failure when the check is known to fail on this page.
export function knownFailure(test: Pick<TestType<any, any>, "fail">, check: string, page: string): void {
  const known = KNOWN[check];
  if (known && (known.pages === "all" || known.pages.includes(page))) {
    test.fail(true, known.reason);
  }
}
