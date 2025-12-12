import { FilterKeyword } from "../../../components/shared/keyword-filter-generic/keyword-filter-generic.component";

/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
export class FilterValueGeneric {
  constructor(args: { value?: string; hiddenValue?: string } = {}) {
    this._value = args.value ? args.value : "";
    this._hiddenValue = args.hiddenValue ? args.hiddenValue : "";
  }

  private _value: string;

  get value(): string {
    return this._value;
  }

  private _hiddenValue: string;

  get hiddenValue(): string {
    return this._hiddenValue;
  }

  get isEmpty(): boolean {
    return this._value.length === 0;
  }

  get isNotEmpty(): boolean {
    return this._value.length > 0;
  }

  get filterString(): string {
    return this._value;
  }

  set setString(newValue: string) {
    this._value = newValue;
  }

  get filterMap(): Map<string, string> {
    return parseToMap(this._value);
  }

  get hiddenFilterMap(): Map<string, string> {
    return parseToMap(this._hiddenValue);
  }

  public copyWith(args?: { value?: string; hiddenValue?: string }): FilterValueGeneric {
    const newFilter = new FilterValueGeneric({
      value: args?.value ?? this._value,
      hiddenValue: args?.hiddenValue ?? this._hiddenValue
    });
    return newFilter;
  }

  public addKey(filterKeyword: FilterKeyword): FilterValueGeneric {
    // Adds a new filterKeyword to the string if it does not already exist.
    if (!keyPresenceRe(filterKeyword.key).test(this._value)) {
      this._value = this._value ? `${this._value.trim()} ${filterKeyword}: ` : `${filterKeyword}: `;
    }
    return new FilterValueGeneric({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public addHiddenKey(filterKeyword: FilterKeyword): FilterValueGeneric {
    // Adds a new filterKeyword to the string if it does not already exist.
    if (!keyPresenceRe(filterKeyword.key).test(this._hiddenValue)) {
      this._hiddenValue = this._hiddenValue ? `${this._hiddenValue.trim()} ${filterKeyword}: ` : `${filterKeyword}: `;
    }
    return new FilterValueGeneric({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public getValueOfKey(key: string): string | undefined {
    return this.filterMap.get(key);
  }

  public removeKey(key: string): FilterValueGeneric {
    this._value = this._value.replace(keySegmentRe(key), "").trim().replace(/\s+/g, " ");
    return new FilterValueGeneric({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public removeHiddenKey(key: string): FilterValueGeneric {
    this._hiddenValue = this._hiddenValue.replace(keySegmentRe(key), "").trim().replace(/\s+/g, " ");
    return new FilterValueGeneric({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public hasKey(key: string): boolean {
    return keyPresenceRe(key).test(this._value);
  }

  public toggleKey(filterKeyword: FilterKeyword): FilterValueGeneric {
    if (filterKeyword.toggleKeyword) {
      return filterKeyword.toggleKeyword(this);
    }
    if (this.hasKey(filterKeyword.key)) {
      return this.removeKey(filterKeyword.key);
    } else {
      return this.addKey(filterKeyword);
    }
  }

  public getFilterIconName(filterKeyword: FilterKeyword): "remove_circle" | "add_circle" | "change_circle" {
    if (filterKeyword.getIconName) {
      return filterKeyword.getIconName(this);
    }
    return this.hasKey(filterKeyword.key) ? "remove_circle" : "add_circle";
  }

  /**
   * Adds a new entry to the filter value.
   * If the keyword already exists, it updates the value.
   * @param keyword The keyword to add or update.
   * @param value The value associated with the keyword.
   */
  public addEntry(keyword: string, value: string): FilterValueGeneric {
    const map = this.filterMap;
    map.set(keyword, value);
    this.setFromMap(map);
    return new FilterValueGeneric({ value: this._value, hiddenValue: this._hiddenValue });
  }

  /**
   * Sets the filter value from a map of key-value pairs.
   * Converts the map to the normalized string format and updates _value.
   */
  public setFromMap(map: Map<string, string>): void {
    const needsQuoting = (v: string) => /[\s"']/.test(v);
    const quoteAndEscape = (v: string) => `"${v.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`; // double-quote strategy

    const entries: string[] = [];
    map.forEach((value, key) => {
      const val = value ?? "";
      const rendered = val === "" ? "" : needsQuoting(val) ? quoteAndEscape(val) : val;
      entries.push(`${key}: ${rendered}`);
    });
    this._value = entries.join(" ").trim();
  }

  /**
   * Sets the hidden filter value from a map of key-value pairs.
   * Converts the map to the normalized string format and updates _hiddenValue.
   */
  public setHiddenFromMap(map: Map<string, string>): void {
    const entries: string[] = [];
    map.forEach((value, key) => {
      entries.push(`${key}: ${value}`);
    });
    this._hiddenValue = entries.join(" ");
  }

  /**
   * Adds or updates a hidden (key: value) pair in hiddenValue.
   */
  public updateHiddenEntry(key: string, value: string): FilterValueGeneric {
    const map = this.hiddenFilterMap;
    map.set(key, value);
    this.setHiddenFromMap(map);
    return new FilterValueGeneric({ value: this._value, hiddenValue: this._hiddenValue });
  }
}

const PAIR_RE_SRC = String.raw`(?<=^|\s)([A-Za-z0-9_]+):\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|(.*?))(?=\s*(?:[A-Za-z0-9_]+:|$))`;

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function keySegmentRe(keyword: string): RegExp {
  return new RegExp(`(?<=^|\\s)(${keyword}):\\s*(?:"[^"]*"|'[^']*'|.*?)(?=\\s*(?:[A-Za-z0-9_]+:|$))`, "g");
}

function keyPresenceRe(keyword: string): RegExp {
  const k = escapeRe(keyword);
  return new RegExp(`(?<=^|\\s)(${k}):(?=\\s|$)`, "g");
}

function parseToMap(text: string): Map<string, string> {
  const re = new RegExp(PAIR_RE_SRC, "g");
  const map = new Map<string, string>();
  let m: RegExpExecArray | null;

  while ((m = re.exec(text)) !== null) {
    const filterKeyword = m[1];
    const valRaw =
      m[2] != null
        ? m[2].replace(/\\"/g, '"').replace(/\\\\/g, "\\")
        : m[3] != null
          ? m[3].replace(/\\'/g, "'").replace(/\\\\/g, "\\")
          : (m[4] ?? "").trim();

    if (valRaw.trim() === "*") {
      continue;
    }

    map.set(filterKeyword, valRaw);
  }

  return map;
}
