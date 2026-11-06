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
import { configureAxe } from "jest-axe";

/**
 * Runs axe-core with the WCAG 2.2 Level A and AA rules on a rendered element:
 *
 *   expect(await axe(fixture.nativeElement)).toHaveNoViolations();
 *
 * Only rules tagged as WCAG run; axe skips the best-practice rules ("region", "heading-order"), which need a full page,
 * and the experimental ones. When to add a check, what it covers and its pitfalls: dev/webui-accessibility-tests.md.
 */
export const axe = configureAxe({
  runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"] },
  // The colour rules need a layout, which jsdom lacks. jest-axe turns them off globally, but a run by tag ignores that.
  rules: { "color-contrast": { enabled: false }, "link-in-text-block": { enabled: false } },
  // Full details (selector, HTML snippet) only for violations; the other result types are not read.
  resultTypes: ["violations"]
});

/**
 * Timeout for an axe check on a large component, where axe alone takes more than half a second: when all Jest workers
 * are busy, that can exceed the default of 5 seconds. Pass it as the third argument of the check's `it`.
 */
export const AXE_TIMEOUT = 15_000;
