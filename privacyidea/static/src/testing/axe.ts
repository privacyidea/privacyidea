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
 * Only rules tagged as WCAG run: the best-practice rules ("region", "heading-order") need a full page. jest-axe turns
 * off the colour rules, as jsdom has no layout. When to add a check, what it covers and its pitfalls:
 * dev/webui-accessibility-tests.md.
 */
export const axe = configureAxe({
  runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"] }
});
