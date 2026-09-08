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
import { Component, computed, input } from "@angular/core";

import { AuthenticationLogEntry } from "@services/authentication-log/authentication-log.service";

import { REASON_DETAIL_INFO_KEY } from "../../reason-detail";

// other_info keys another column shows, and this one therefore skips. The reason detail is a nested map explaining the
// row's reasons: folded into this column it could only be a one-line JSON dump, so the Reasons column offers it as a
// dialog instead (see ReasonCell) and nothing is lost by leaving it out here.
const KEYS_SHOWN_ELSEWHERE: readonly string[] = [REASON_DETAIL_INFO_KEY];

// Fragments that are an acronym rather than a word, so a humanized key reads "Source IP" and not "Source ip".
const INFO_KEY_ACRONYMS: Record<string, string> = {
  // transaction_id, attempt_id
  id: "ID",
  // source_ip
  ip: "IP",
  uid: "UID"
};

// A rendered other_info row: a leaf carries `value`, a one-level-nested dict *or list* carries `children` (rendered as
// a bulleted sub-list), and anything deeper is folded into the leaf value as compact JSON.
export interface InfoRow {
  // Empty for an element of a list, which has no key of its own - the bullet is what marks it.
  key: string;
  value: string;
}

export interface InfoEntry {
  key: string;
  value?: string;
  children?: InfoRow[];
}

/**
 * Whether the Info cell would render anything for this entry: an `other_info` with at least one key the cell actually
 * shows. Asked by the table before it sizes the Info column, so a row whose only key is one the cell skips (see
 * KEYS_SHOWN_ELSEWHERE) does not make the column claim its width for an empty cell.
 */
export function hasInfoContent(info: AuthenticationLogEntry["other_info"]): boolean {
  return !!info && Object.keys(info).some((key) => !KEYS_SHOWN_ELSEWHERE.includes(key));
}

/**
 * The authentication log's Info cell: `other_info` as "Key: value" rows.
 *
 * Scalars are shown as they are, and one level of nesting - a dict (the `truncated` overflow, the only thing the
 * backend puts here) or a list - becomes a bulleted sub-list under its key. Anything deeper is folded into compact
 * JSON, which is honest for a payload nothing writes today and better than silently dropping it.
 *
 * What another column already shows is skipped (see KEYS_SHOWN_ELSEWHERE), so the same value is not read twice - once
 * here as JSON and once there in a form that fits it.
 *
 * Deliberately generic, and deliberately *not* shared with the Conditional access cell: this one walks arbitrary JSON,
 * while an outcome has one known shape. They share their looks (../info-list), not their rendering.
 */
@Component({
  selector: "app-info-cell",
  standalone: true,
  templateUrl: "./info-cell.html",
  styleUrl: "./info-cell.scss"
})
export class InfoCell {
  // Whatever the backend put in other_info, or nothing. A free-form JSON column, so the value type stops at "a record".
  readonly info = input<AuthenticationLogEntry["other_info"]>(null);

  readonly entries = computed<InfoEntry[]>(() => {
    const info = this.info();
    // The guard is not redundant with the input's type: the table's skeleton rows are built by column key and set every
    // column to "", so the declared type is a promise the loading state breaks.
    if (!this.isPlainObject(info)) return [];
    const shown = Object.entries(info).filter(([key]) => !KEYS_SHOWN_ELSEWHERE.includes(key));
    return shown.map(([key, raw]) => {
      const label = this.humanizeKey(key);
      if (this.isPlainObject(raw)) {
        return { key: label, children: this.rows(raw) };
      }
      // A list is the same layer of nesting as a dict, so it reads the same way: one bullet per element, keyless.
      if (Array.isArray(raw)) {
        return { key: label, children: raw.map((item) => ({ key: "", value: this.formatValue(item) })) };
      }
      return { key: label, value: this.formatValue(raw) };
    });
  });

  private rows(value: Record<string, unknown>): InfoRow[] {
    return Object.entries(value).map(([key, raw]) => ({ key: this.humanizeKey(key), value: this.formatValue(raw) }));
  }

  // "policy_name" -> "Policy name", "source_ip" -> "Source IP". Keeps the raw key when it carries no underscores and
  // is already capitalized, so acronym-only keys are not mangled.
  private humanizeKey(key: string): string {
    const words = key.split("_").filter((word) => word.length > 0);
    if (!words.length) return key;
    return words
      .map((word, index) => {
        const upper = INFO_KEY_ACRONYMS[word.toLowerCase()];
        if (upper) return upper;
        return index === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word;
      })
      .join(" ");
  }

  private formatValue(value: unknown): string {
    if (value === null || value === undefined) return "";
    if (Array.isArray(value)) return value.map((entry) => this.formatValue(entry)).join(", ");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  private isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }
}
