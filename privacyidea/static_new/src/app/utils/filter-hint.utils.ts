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

/**
 * Human readable hint describing how a single filter keyword matches its value.
 * Exact-match keywords compare the whole value; all others match substrings via
 * an automatically applied `*value*` wildcard.
 */
export function filterMatchHint(exactMatch: boolean): string {
  return exactMatch ? $localize`Matches the exact value.` : $localize`Matches any part of the value.`;
}

export interface FilterKeywordSemantics {
  exactMatch: boolean;
  caseSensitive: boolean;
  isBoolean: boolean;
}

/**
 * Tooltip for a column filter icon: the "Filter by X" title plus a per-keyword
 * description of how the value is matched. Boolean keywords take a true/false
 * value and ignore wildcards and case entirely.
 */
export function filterColumnHint(label: string, semantics: FilterKeywordSemantics): string {
  const lines = [$localize`Filter by ${label}`];
  if (semantics.isBoolean) {
    lines.push($localize`Enter true or false.`);
    return lines.join("\n");
  }
  lines.push(filterMatchHint(semantics.exactMatch));
  lines.push(semantics.caseSensitive ? $localize`Case-sensitive.` : $localize`Case-insensitive.`);
  return lines.join("\n");
}
