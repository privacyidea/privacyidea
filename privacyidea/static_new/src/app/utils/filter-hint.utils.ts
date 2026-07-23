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

export interface FilterInputHintOptions {
  supportsKeywords?: boolean;
  /** Some keywords are matched without normalising case, so the database or resolver decides. */
  mayBeCaseSensitive?: boolean;
}

/**
 * Tooltip for a filter input: what the placeholder does not already show.
 * Per-keyword details belong on the column filter icons.
 */
export function filterInputHint(options: FilterInputHintOptions = {}): string {
  const lines: string[] = [];
  if (options.supportsKeywords ?? true) {
    lines.push($localize`Quote values with spaces or colons: description: "note: 2fa"`);
  }
  lines.push($localize`Wildcard: * where partial match is supported`);
  lines.push(options.mayBeCaseSensitive ? $localize`Mostly case-insensitive` : $localize`Case-insensitive`);
  return lines.join("\n");
}

/**
 * Hint below a filter input: the keywords the filter accepts. Shown as static
 * text so the keywords are readable without hovering the input.
 */
export function filterKeywordHint(keywords: string[]): string {
  if (!keywords.length) {
    return "";
  }
  return $localize`Keywords: ${keywords.join(", ")}`;
}

/**
 * How a keyword deviates from its filter's overall case behaviour.
 * "usually-*" means the database or resolver decides.
 */
export type FilterCaseNote = "usually-insensitive" | "usually-sensitive" | "sensitive";

export interface FilterKeywordSemantics {
  exactMatch: boolean;
  isBoolean: boolean;
  isUnsupported?: boolean;
  caseNote?: FilterCaseNote;
}

/**
 * Tooltip for a column filter icon: the "Filter by X" title plus a short,
 * comma separated summary of how the value is matched.
 */
export function filterColumnHint(label: string, semantics: FilterKeywordSemantics): string {
  const title = $localize`Filter by ${label}`;
  if (semantics.isUnsupported) {
    return `${title}\n` + $localize`currently not supported`;
  }
  if (semantics.isBoolean) {
    return `${title}\n` + $localize`true or false`;
  }
  const parts: string[] = [];
  parts.push(semantics.exactMatch ? $localize`exact match` : $localize`partial match`);
  if (semantics.caseNote) {
    parts.push(caseNoteText(semantics.caseNote));
  }
  return `${title}\n${parts.join(", ")}`;
}

function caseNoteText(note: FilterCaseNote): string {
  switch (note) {
    case "sensitive":
      return $localize`case-sensitive`;
    case "usually-sensitive":
      return $localize`usually case-sensitive`;
    default:
      return $localize`usually case-insensitive`;
  }
}
