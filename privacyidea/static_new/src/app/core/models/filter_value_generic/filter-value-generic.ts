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

import { DummyFilterOption, FilterOption } from "./filter-option";

export class FilterValueGeneric<T> {
  // --- Members ---
  readonly filterMap: Map<string, FilterOption<T>>;
  readonly hiddenFilterMap: Map<string, FilterOption<T>>;
  readonly allFilters: FilterOption<T>[];
  readonly availableFilters: Map<string, FilterOption<T>>;

  // --- Constructor ---
  constructor(
    args:
      | {
      availableFilters: FilterOption<T>[];
      filterMap?: Map<string, FilterOption<T>>;
      hiddenFilterMap?: Map<string, FilterOption<T>>;
    }
      | {
      availableFiltersMap: Map<string, FilterOption<T>>;
      filterMap?: Map<string, FilterOption<T>>;
      hiddenFilterMap?: Map<string, FilterOption<T>>;
    }
  ) {
    if ("availableFilters" in args) {
      this.availableFilters = args.availableFilters.reduce(
        (map, option) => map.set(option.key, option),
        new Map<string, FilterOption<T>>()
      );
    } else {
      this.availableFilters = args.availableFiltersMap;
    }
    this.filterMap = args.filterMap ?? new Map<string, FilterOption<T>>();
    this.hiddenFilterMap = args.hiddenFilterMap ?? new Map<string, FilterOption<T>>();
    this.allFilters = [...this.filterMap.values(), ...this.hiddenFilterMap.values()];
  }

  // --- Getters / State ---
  get isEmpty(): boolean {
    return this.filterMap.size === 0;
  }

  get isNotEmpty(): boolean {
    return this.filterMap.size > 0;
  }

  get hiddenIsEmpty(): boolean {
    return this.hiddenFilterMap.size === 0;
  }

  get hiddenIsNotEmpty(): boolean {
    return this.hiddenFilterMap.size > 0;
  }

  get hasActiveFilters(): boolean {
    return this.filterMap.size > 0 || this.hiddenFilterMap.size > 0;
  }

  get rawValue(): string {
    return Array.from(this.filterMap.values())
      .map((option) => {
        const isDummy = option instanceof DummyFilterOption;
        if (isDummy && option.value === null) {
          return option.key;
        }
        return `${option.key}: ${option.value ?? ""}`;
      })
      .join(" ");
  }

  /**
   * The keyword-less search terms: standalone words entered without a column keyword. Used to
   * highlight where a free-text match occurred across columns.
   */
  get freeTextTerms(): string[] {
    return Array.from(this.filterMap.values())
      .filter((option) => option instanceof DummyFilterOption && option.value === null)
      .map((option) => option.key);
  }

  get apiFilterString(): string {
    return Array.from([...this.filterMap.values(), ...this.hiddenFilterMap.values()])
      .filter((option) => !(option instanceof DummyFilterOption))
      .filter((option) => option.value !== null && !/^\**$/.test(option.value!))
      .map((option) => `${option.key}: ${option.value}`)
      .join(" ");
  }

  // --- Public API ---
  public matches(item: T): boolean {
    return this.allFilters.every((filter) => {
      // A standalone word (no keyword) is stored as a DummyFilterOption with a null value.
      // Treat it as a keyword-less free-text term matched across all searchable columns.
      if (filter instanceof DummyFilterOption && filter.value === null) {
        return this.matchesFreeText(item, filter.key);
      }
      return filter.matches(item, this);
    });
  }

  /**
   * Matches a keyword-less search term against every column that opts into global search via
   * FilterOption.globalMatches (OR across columns). If no column opts in, free-text is a no-op.
   */
  private matchesFreeText(item: T, term: string): boolean {
    const normalized = term.toLowerCase();
    const searchable = Array.from(this.availableFilters.values()).filter((option) => option.globalMatches);
    if (searchable.length === 0) return true;
    return searchable.some((option) => option.globalMatches!(item, normalized));
  }

  public filterItems(unfiltered: T[]): T[] {
    if (!unfiltered?.length) return [];
    if (this.isEmpty && this.hiddenIsEmpty) return unfiltered;

    return unfiltered.filter((item) => this.matches(item));
  }

  public hasKey(key: string): boolean {
    return this.filterMap.has(key);
  }

  public getOptionForKey(key: string): FilterOption<T> | undefined {
    return this.availableFilters.get(key);
  }

  public getFilterOfKey(key: string): string | null | undefined {
    if (this.filterMap.has(key)) return this.filterMap.get(key)!.value;
    if (this.hiddenFilterMap.has(key)) return this.hiddenFilterMap.get(key)!.value;
    return undefined;
  }

  public addKey(key: string): FilterValueGeneric<T> {
    const optionFromMap = this.availableFilters.get(key);
    const newFilterMap = new Map(this.filterMap);
    if (!optionFromMap) {
      newFilterMap.set(key, new DummyFilterOption({ key }));
    } else {
      newFilterMap.set(key, optionFromMap);
    }
    return this._copyWith({ filterMap: newFilterMap });
  }

  /**
   * Adds a free-text term. Unlike addKey, it is always stored as a cross-column DummyFilterOption,
   * even when the term equals a registered key — so a bare word never becomes a match-all no-op.
   */
  public addFreeText(term: string): FilterValueGeneric<T> {
    const newFilterMap = new Map(this.filterMap);
    newFilterMap.set(term, new DummyFilterOption({ key: term }));
    return this._copyWith({ filterMap: newFilterMap });
  }

  public addOption(option: FilterOption<T>): FilterValueGeneric<T> {
    const newFilterMap = new Map(this.filterMap);
    return this._copyWith({ filterMap: newFilterMap.set(option.key, option) });
  }

  public addHiddenKey(key: string): FilterValueGeneric<T> {
    const optionFromMap = this.availableFilters.get(key);
    if (!optionFromMap) {
      throw new Error(`FilterOption for key "${key}" not found.`);
    }
    const newHiddenFilterMap = new Map(this.hiddenFilterMap);
    return this._copyWith({ hiddenFilterMap: newHiddenFilterMap.set(key, optionFromMap) });
  }

  public setValueOfKey(key: string, value: string | null): FilterValueGeneric<T> {
    if (this.filterMap.has(key)) {
      const newFilterMap = new Map(this.filterMap);
      newFilterMap.set(key, newFilterMap.get(key)!.withValue(value));
      return this._copyWith({ filterMap: newFilterMap });
    }
    return this.addKey(key).setValueOfKey(key, value);
  }

  public setValueOfHiddenKey(key: string, value: string): FilterValueGeneric<T> {
    if (this.hiddenFilterMap.has(key)) {
      const newHiddenFilterMap = new Map(this.hiddenFilterMap);
      newHiddenFilterMap.set(key, newHiddenFilterMap.get(key)!.withValue(value));
      return this._copyWith({ hiddenFilterMap: newHiddenFilterMap });
    }
    return this.addHiddenKey(key).setValueOfHiddenKey(key, value);
  }

  public removeKey(key: string): FilterValueGeneric<T> {
    const newFilterMap = new Map(this.filterMap);
    if (newFilterMap.delete(key)) {
      return this._copyWith({ filterMap: newFilterMap });
    }
    return this;
  }

  public toggleKey(key: string): FilterValueGeneric<T> {
    return this.hasKey(key) ? this.removeKey(key) : this.addKey(key);
  }

  public setByString(rawValue: string): FilterValueGeneric<T> {
    const newMap = parseToMap(rawValue.trim().toLocaleLowerCase());
    let instance: FilterValueGeneric<T> = this._copyWith({ filterMap: new Map() });
    newMap.forEach((value, key) => {
      // A null value marks a standalone word (no `key:`): add it as free text, not a keyword filter.
      instance = value === null ? instance.addFreeText(key) : instance.setValueOfKey(key, value);
    });
    return instance;
  }

  public clear(): FilterValueGeneric<T> {
    return this._copyWith({
      filterMap: new Map(),
      hiddenFilterMap: new Map()
    });
  }

  // --- Private Helpers ---
  private _copyWith(args?: {
    filterMap?: Map<string, FilterOption<T>>;
    hiddenFilterMap?: Map<string, FilterOption<T>>;
  }): FilterValueGeneric<T> {
    return new FilterValueGeneric<T>({
      availableFiltersMap: this.availableFilters,
      filterMap: args?.filterMap ?? this.filterMap,
      hiddenFilterMap: args?.hiddenFilterMap ?? this.hiddenFilterMap
    });
  }
}

// --- Modular Parser Constants ---
const RE_KEY = /^[A-Za-z0-9_-]+/;
const RE_COLON_WHITESPACE = /^(\s*:\s*)/;
const RE_QUOTED_DBL = /^"((?:\\.|[^"\\])*)"/;
const RE_QUOTED_SNG = /^'((?:\\.|[^'\\])*)'/;
const RE_UNQUOTED = /^((?:(?!\s+[A-Za-z0-9_]+\s*:)[^ ])+)/;

function parseToMap(text: string): Map<string, string | null> {
  const map = new Map<string, string | null>();
  let remaining = text.trim();

  while (remaining.length > 0) {
    const keyMatch = remaining.match(RE_KEY);
    if (!keyMatch) {
      remaining = remaining.slice(1).trim();
      continue;
    }
    const key = keyMatch[0];
    let tempRemaining = remaining.slice(key.length);

    const colonMatch = tempRemaining.match(RE_COLON_WHITESPACE);
    if (!colonMatch) {
      map.set(key, null);
      remaining = tempRemaining.trim();
      continue;
    }

    const colonStr = colonMatch[0];
    tempRemaining = tempRemaining.slice(colonStr.length);

    let value: string | null;
    let valMatch: RegExpMatchArray | null;

    if ((valMatch = tempRemaining.match(RE_QUOTED_DBL))) {
      value = valMatch[1].replace(/\\"/g, "\"").replace(/\\\\/g, "\\");
      remaining = tempRemaining.slice(valMatch[0].length).trim();
    } else if ((valMatch = tempRemaining.match(RE_QUOTED_SNG))) {
      value = valMatch[1].replace(/\\'/g, "'").replace(/\\\\/g, "\\");
      remaining = tempRemaining.slice(valMatch[0].length).trim();
    } else {
      // Logic for unquoted values:
      // If there is whitespace after the colon AND the next thing looks like 'key:',
      // we treat the current value as empty.
      const hasTrailingSpaceInColon =
        colonStr.endsWith(" ") || (tempRemaining.length > 0 && tempRemaining.startsWith(" "));
      const nextKeyCandidate = tempRemaining.match(RE_KEY);
      const followedByColon =
        nextKeyCandidate && tempRemaining.slice(nextKeyCandidate[0].length).match(RE_COLON_WHITESPACE);

      if (hasTrailingSpaceInColon && followedByColon) {
        value = "";
        remaining = tempRemaining.trim();
      } else {
        valMatch = tempRemaining.match(RE_UNQUOTED);
        if (valMatch) {
          value = valMatch[1].replace(/\\\\/g, "\\");
          remaining = tempRemaining.slice(valMatch[0].length).trim();
        } else {
          value = "";
          remaining = tempRemaining.trim();
        }
      }
    }
    map.set(key, value);
  }
  return map;
}
