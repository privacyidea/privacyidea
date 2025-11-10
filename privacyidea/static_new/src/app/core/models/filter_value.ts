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
export class FilterValue {
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

  public copyWith(args?: { value?: string; hiddenValue?: string }): FilterValue {
    const newFilter = new FilterValue({
      value: args?.value ?? this._value,
      hiddenValue: args?.hiddenValue ?? this._hiddenValue
    });
    return newFilter;
  }

  public addKey(key: string): FilterValue {
    // Adds a new key to the string if it does not already exist.
    if (!keyPresenceRe(key).test(this._value)) {
      this._value = this._value ? `${this._value.trim()} ${key}: ` : `${key}: `;
    }
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public addHiddenKey(key: string): FilterValue {
    // Adds a new key to the string if it does not already exist.
    if (!keyPresenceRe(key).test(this._hiddenValue)) {
      this._hiddenValue = this._hiddenValue ? `${this._hiddenValue.trim()} ${key}: ` : `${key}: `;
    }
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public getValueOfKey(key: string): string | undefined {
    return this.filterMap.get(key);
  }

  public removeKey(key: string): FilterValue {
    this._value = this._value.replace(keySegmentRe(key), "").trim().replace(/\s+/g, " ");
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public removeHiddenKey(key: string): FilterValue {
    this._hiddenValue = this._hiddenValue.replace(keySegmentRe(key), "").trim().replace(/\s+/g, " ");
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public hasKey(key: string): boolean {
    return keyPresenceRe(key).test(this._value);
  }

  public toggleKey(key: string): FilterValue {
    if (this.hasKey(key)) {
      return this.removeKey(key);
    } else {
      return this.addKey(key);
    }
  }

  /**
   * Adds a new entry to the filter value.
   * If the key already exists, it updates the value.
   * @param key The key to add or update.
   * @param value The value associated with the key.
   */
  public addEntry(key: string, value: string): FilterValue {
    const map = this.filterMap;
    map.set(key, value);
    this.setFromMap(map);
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }

  /**
   * Sets the filter value from a map of key-value pairs.
   * Converts the map to the normalized string format and updates _value.
   */
  public setFromMap(map: Map<string, string>): void {
    const needsQuoting = (v: string) => /[\s"']/.test(v);
    const quoteAndEscape = (v: string) =>
      `"${v.replace(/\\/g, "\\\\").replace(/"/g, "\\\"")}"`; // double-quote strategy

    const entries: string[] = [];
    map.forEach((value, key) => {
      const val = value ?? "";
      const rendered = val === "" ? "" : (needsQuoting(val) ? quoteAndEscape(val) : val);
      entries.push(`${key}: ${rendered}`);
    });
    this._value = entries.join(" ").trim();
  }
}

const PAIR_RE_SRC =
  String.raw`(?<=^|\s)([A-Za-z0-9_]+):\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|(.*?))(?=\s*(?:[A-Za-z0-9_]+:|$))`;

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function keySegmentRe(key: string): RegExp {
  return new RegExp(
    `(?<=^|\\s)(${key}):\\s*(?:"[^"]*"|'[^']*'|.*?)(?=\\s*(?:[A-Za-z0-9_]+:|$))`,
    "g"
  );
}

function keyPresenceRe(key: string): RegExp {
  const k = escapeRe(key);
  return new RegExp(`(?<=^|\\s)(${k}):(?=\\s|$)`, "g");
}

function parseToMap(text: string): Map<string, string> {
  const re = new RegExp(PAIR_RE_SRC, "g");
  const map = new Map<string, string>();
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const key = m[1];
    const val =
      m[2] != null
        ? m[2].replace(/\\\\/g, "\\").replace(/\\"/g, "\"")
        : m[3] != null
          ? m[3].replace(/\\\\/g, "\\").replace(/\\'/g, "'")
          : (m[4] ?? "").trim();
    map.set(key, val);
  }
  return map;
}