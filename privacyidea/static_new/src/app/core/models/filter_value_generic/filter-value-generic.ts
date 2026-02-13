/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { FilterOption, DummyFilterOption } from "./filter-option";

export class FilterValueGeneric<T> {
  readonly filterMap: Map<string, FilterOption<T>>;
  readonly hiddenFilterMap: Map<string, FilterOption<T>>;
  readonly availableFilters: Map<string, FilterOption<T>>;

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
  }

  get isEmpty(): boolean {
    return this.filterMap.size === 0;
  }

  get hiddenIsEmpty(): boolean {
    return this.hiddenFilterMap.size === 0;
  }

  get isNotEmpty(): boolean {
    return this.filterMap.size > 0;
  }

  get hiddenIsNotEmpty(): boolean {
    return this.hiddenFilterMap.size > 0;
  }

  get rawValue(): string {
    return Array.from(this.filterMap.values())
      .map((option) => {
        const isDummy = (option as any).isDummy;
        if (isDummy && option.value === null) {
          return option.key;
        }
        return `${option.key}: ${option.value ?? ""}`;
      })
      .join(" ");
  }

  get apiFilterString(): string {
    return Array.from([...this.filterMap.values(), ...this.hiddenFilterMap.values()])
      .filter((option) => !(option as any).isDummy)
      .filter((option) => option.value !== null && !/^\**$/.test(option.value!))
      .map((option) => `${option.key}: ${option.value}`)
      .join(" ");
  }

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

  filterItems(unfiltered: T[]): T[] {
    if (!unfiltered?.length) return [];
    if (this.isEmpty && this.hiddenIsEmpty) return unfiltered;

    const allFilters = [...this.filterMap.values(), ...this.hiddenFilterMap.values()];
    return unfiltered.filter((item) => allFilters.every((filter) => filter.matches(item, this)));
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

  public getOptionForKey(key: string): FilterOption<T> | undefined {
    return this.availableFilters.get(key);
  }

  /**
   * Safe lookup that distinguishes between null (key exists, no value) and undefined.
   */
  public getValueOfKey(key: string): string | null | undefined {
    if (this.filterMap.has(key)) return this.filterMap.get(key)!.value;
    if (this.hiddenFilterMap.has(key)) return this.hiddenFilterMap.get(key)!.value;
    return undefined;
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

  public hasKey(key: string): boolean {
    return this.filterMap.has(key);
  }

  public toggleKey(key: string): FilterValueGeneric<T> {
    return this.hasKey(key) ? this.removeKey(key) : this.addKey(key);
  }

  public getFilterIconNameOf(filterKeyword: FilterOption<T>): string {
    if (filterKeyword.getIconName) {
      return filterKeyword.getIconName(this);
    }
    return this.hasKey(filterKeyword.key) ? "remove_circle" : "add_circle";
  }

  public setByString(rawValue: string): FilterValueGeneric<T> {
    const newMap = parseToMap(rawValue.trim().toLocaleLowerCase());
    let instance: FilterValueGeneric<T> = this._copyWith({ filterMap: new Map() });
    newMap.forEach((value, key) => {
      instance = instance.setValueOfKey(key, value);
    });
    return instance;
  }

  public clear(): FilterValueGeneric<T> {
    return this._copyWith({
      filterMap: new Map(),
      hiddenFilterMap: new Map()
    });
  }
}

/**
 * Modular Parser Constants
 */
const RE_KEY = /^[A-Za-z0-9_]+/;
const RE_COLON_WHITESPACE = /^(\s*:\s*)/;
const RE_QUOTED_DBL = /^"((?:\\.|[^"\\])*)"/;
const RE_QUOTED_SNG = /^'((?:\\.|[^'\\])*)'/;
const RE_UNQUOTED = /^((?:(?!\s+[A-Za-z0-9_]+\s*:)[^ ])+)/;

function parseToMap(text: string): Map<string, string | null> {
  const map = new Map<string, string | null>();
  let remaining = text.trim();

  while (remaining.length > 0) {
    // 1. Match Key
    const keyMatch = remaining.match(RE_KEY);
    if (!keyMatch) {
      remaining = remaining.slice(1).trim();
      continue;
    }
    const key = keyMatch[0];
    let tempRemaining = remaining.slice(key.length);

    // 2. Check for Colon
    const colonMatch = tempRemaining.match(RE_COLON_WHITESPACE);
    if (!colonMatch) {
      // Standalone dummy key
      map.set(key, null);
      remaining = tempRemaining.trim();
      continue;
    }

    const colonStr = colonMatch[0];
    tempRemaining = tempRemaining.slice(colonStr.length);

    // 3. Handle Value
    let value: string | null = "";
    let valMatch: RegExpMatchArray | null = null;

    if ((valMatch = tempRemaining.match(RE_QUOTED_DBL))) {
      value = valMatch[1].replace(/\\"/g, '"').replace(/\\\\/g, "\\");
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
        value = ""; // Found 'key1: key2:' scenario
        remaining = tempRemaining.trim();
      } else {
        valMatch = tempRemaining.match(RE_UNQUOTED);
        if (valMatch) {
          value = valMatch[1].replace(/\\\\/g, "\\");
          remaining = tempRemaining.slice(valMatch[0].length).trim();
        } else {
          value = ""; // Fallback for 'key:' at end of string
          remaining = tempRemaining.trim();
        }
      }
    }
    map.set(key, value);
  }
  return map;
}
