import {
  DummyFilterOption,
  FilterOption
} from "../../../components/shared/keyword-filter-generic/keyword-filter-generic.component";

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
export class FilterValueGeneric<T> {
  constructor(
    args:
      | {
          availableFilters: FilterOption<T>[];
          filterMap?: Map<string, FilterOption>;
          hiddenFilterMap?: Map<string, FilterOption>;
        }
      | {
          availableFiltersMap: Map<string, FilterOption<T>>;
          filterMap?: Map<string, FilterOption>;
          hiddenFilterMap?: Map<string, FilterOption>;
        }
  ) {
    if ("availableFilters" in args) {
      this.availableFilters = args.availableFilters.reduce(
        (map, option) => map.set(option.key, option),
        new Map<string, FilterOption<T>>()
      );
    } else if ("availableFiltersMap" in args) {
      this.availableFilters = args.availableFiltersMap;
    }
    this.filterMap = args.filterMap ?? new Map<string, FilterOption>();
    this.hiddenFilterMap = args.hiddenFilterMap ?? new Map<string, FilterOption>();
  }

  // // private _value: string;

  // get value(): string {
  //   return this._value;
  // }

  // // private _hiddenValue: string;

  // get hiddenValue(): string {
  //   return this._hiddenValue;
  // }

  /**
   * Returns true when there is no visible filter set.
   */
  get isEmpty(): boolean {
    return this.filterMap.size === 0;
  }

  /**
   * Returns true when there is no hidden filter set.
   */
  get hiddenIsEmpty(): boolean {
    return this.hiddenFilterMap.size === 0;
  }

  /**
   * Returns true when there is at least one visible filter set.
   */
  get isNotEmpty(): boolean {
    return this.filterMap.size > 0;
  }

  /**
   * Returns true when there is at least one hidden filter set.
   */
  get hiddenIsNotEmpty(): boolean {
    return this.hiddenFilterMap.size > 0;
  }

  get filterString(): string {
    const array = Array.from(this.filterMap.values());
    const filterStrings = array.map((option) => {
      if ((option as any).isDummy) {
        // return option.key;
        if (option.value === null) {
          return option.key;
        } else {
          return `${option.key}: ${option.value ?? ""}`;
        }
      } else {
        return `${option.key}: ${option.value ?? ""}`;
      }
    });
    const result = filterStrings.join(" ");
    return result;
  }

  get apiFilterString(): string {
    // Like filterString, but includes hidden filters too (for API calls) and excludes dummies
    // Excludes keys with value undefined or null "" or "*" or "**" or "***" or "*..."
    const array = Array.from([...this.filterMap.values(), ...this.hiddenFilterMap.values()]);
    const filterStrings = array
      .filter((option) => !(option as any).isDummy)
      .filter((option) => option.value !== null && !/^\**$/.test(option.value))
      .map((option) => `${option.key}: ${option.value}`);
    const result = filterStrings.join(" ");
    return result;
  }
  // set setString(newValue: string) {
  //   this._value = newValue;
  // }

  filterMap = new Map<string, FilterOption>();
  hiddenFilterMap = new Map<string, FilterOption>();
  availableFilters = new Map<string, FilterOption>();
  // get filterMap(): Map<string, string> {
  //   return parseToMap(this._value);
  // }

  // get hiddenFilterMap(): Map<string, string> {
  //   return parseToMap(this._hiddenValue);
  // }

  private _copyWith(args?: {
    filterMap?: Map<string, FilterOption>;
    hiddenFilterMap?: Map<string, FilterOption>;
  }): FilterValueGeneric<T> {
    return new FilterValueGeneric<T>({
      availableFiltersMap: this.availableFilters,
      filterMap: args?.filterMap ?? this.filterMap,
      hiddenFilterMap: args?.hiddenFilterMap ?? this.hiddenFilterMap
    });
  }

  filterItems(unfiltered: T[]): T[] {
    if (!unfiltered || unfiltered.length === 0) {
      return [] as T[];
    }
    if (this.filterMap.size === 0 && this.hiddenFilterMap.size === 0) {
      return unfiltered;
    }
    let filtered = [] as T[];
    for (let item of unfiltered) {
      let matchesAll = true;
      for (let filterOption of Array.from([...this.filterMap.values(), ...this.hiddenFilterMap.values()])) {
        if (!filterOption.matches(item, this)) {
          matchesAll = false;
          break;
        }
      }
      if (matchesAll) {
        filtered.push(item);
      }
    }
    return filtered;
  }

  public addKey(key: string): FilterValueGeneric<T> {
    // Adds a new filterKeyword to the string if it does not already exist.
    const optionFromMap = this.availableFilters.get(key);
    if (!optionFromMap) {
      return this._copyWith({
        filterMap: new Map(this.filterMap).set(key, new DummyFilterOption({ key: key }))
      });
    }
    const newFilterMap = new Map(this.filterMap);
    return this._copyWith({
      filterMap: newFilterMap.set(key, optionFromMap)
    });
  }
  public addOption(option: FilterOption): FilterValueGeneric<T> {
    const newFilterMap = new Map(this.filterMap);
    const newAvailableFilters = new Map(this.availableFilters);
    newAvailableFilters.set(option.key, option);
    return this._copyWith({
      filterMap: newFilterMap.set(option.key, option)
    });
  }

  public addHiddenKey(key: string): FilterValueGeneric<T> {
    // Adds a new filterKeyword to the string if it does not already exist.
    const optionFromMap = this.availableFilters.get(key);
    if (!optionFromMap) {
      throw new Error(`FilterOption for key "${key}" not found in available filters.`);
    }
    const newHiddenFilterMap = new Map(this.hiddenFilterMap);
    return this._copyWith({
      hiddenFilterMap: newHiddenFilterMap.set(key, optionFromMap)
    });
  }

  public getOptionForKey(key: string): FilterOption | undefined {
    return this.availableFilters.get(key);
  }
  public getValueOfKey(key: string): string | null | undefined {
    return this.filterMap.get(key)?.value;
  }

  public getOptionForHiddenKey(key: string): FilterOption | undefined {
    return this.hiddenFilterMap.get(key);
  }
  public getValueOfHiddenKey(key: string): string | null | undefined {
    return this.hiddenFilterMap.get(key)?.value;
  }

  public setValueOfKey(key: string, value: string | null): FilterValueGeneric<T> {
    const newFilterMap = new Map(this.filterMap);
    if (newFilterMap.has(key)) {
      const existingOption = newFilterMap.get(key); // Guaranteed to exist due to has() check
      const updatedOption = existingOption!.withValue(value);
      newFilterMap.set(key, updatedOption);
      return this._copyWith({
        filterMap: newFilterMap
      });
    } else {
      return this.addKey(key).setValueOfKey(key, value) ?? this;
    }
  }

  public setValueOfHiddenKey(key: string, value: string): FilterValueGeneric<T> {
    const newHiddenFilterMap = new Map(this.hiddenFilterMap);
    if (newHiddenFilterMap.has(key)) {
      const existingOption = newHiddenFilterMap.get(key); // Guaranteed to exist due to has() check
      const updatedOption = existingOption!.withValue(value);
      newHiddenFilterMap.set(key, updatedOption);
      return this._copyWith({
        hiddenFilterMap: newHiddenFilterMap
      });
    } else {
      return this.addHiddenKey(key).setValueOfHiddenKey(key, value);
    }
  }

  public removeKey(key: string): FilterValueGeneric<T> {
    const newFilterMap = new Map(this.filterMap);
    newFilterMap.delete(key);
    return this._copyWith({
      filterMap: newFilterMap
    });
  }

  public removeHiddenKey(key: string): FilterValueGeneric<T> {
    const newHiddenFilterMap = new Map(this.hiddenFilterMap);
    newHiddenFilterMap.delete(key);
    return this._copyWith({
      hiddenFilterMap: newHiddenFilterMap
    });
  }

  public hasKey(key: string): boolean {
    return this.filterMap.has(key);
  }

  public hasHiddenKey(key: string): boolean {
    return this.hiddenFilterMap.has(key);
  }

  public toggleFilterKeyword(filterKeyword: FilterOption): FilterValueGeneric<T> {
    if (filterKeyword.toggleKeyword) {
      return filterKeyword.toggleKeyword(this);
    }
    return this.toggleKey(filterKeyword.key);
  }

  public toggleKey(key: string): FilterValueGeneric<T> {
    if (this.hasKey(key)) {
      return this.removeKey(key);
    } else {
      return this.addKey(key) ?? this;
    }
  }

  public getFilterIconNameOf(filterKeyword: FilterOption): "remove_circle" | "add_circle" | "change_circle" {
    if (filterKeyword.getIconName) {
      return filterKeyword.getIconName(this);
    }
    return this.hasKey(filterKeyword.key) ? "remove_circle" : "add_circle";
  }

  setByString(filterString: string) {
    const newFilterMap = parseToMap(filterString.trim().toLocaleLowerCase());
    let updatedFilterValue = this._copyWith({
      filterMap: new Map<string, FilterOption>()
    });
    for (let [key, value] of newFilterMap) {
      updatedFilterValue = updatedFilterValue.setValueOfKey(key, value);
    }
    return updatedFilterValue;
  }
}
const PAIR_RE_SRC = String.raw`([A-Za-z0-9_]+):(?:\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|([^ :]+(?![A-Za-z0-9_]*:))))?|([A-Za-z0-9_]+)(?![A-Za-z0-9_]*:)`;

function parseToMap(text: string): Map<string, string | null> {
  const re = new RegExp(PAIR_RE_SRC, "g");
  const map = new Map<string, string | null>();
  let m: RegExpExecArray | null;

  while ((m = re.exec(text)) !== null) {
    if (m.index === re.lastIndex) {
      re.lastIndex++;
    }

    const isKeyWithColon = m[1] !== undefined; // "asd:"
    const filterKeyword = m[1] ?? m[5];
    if (!filterKeyword) continue;

    let valRaw: string | null;

    if (isKeyWithColon) {
      valRaw =
        m[2] != null
          ? m[2].replace(/\\"/g, '"').replace(/\\\\/g, "\\")
          : m[3] != null
            ? m[3].replace(/\\'/g, "'").replace(/\\\\/g, "\\")
            : (m[4] ?? "").trim();
    } else {
      valRaw = null;
    }
    map.set(filterKeyword, valRaw);
  }

  return map;
}
