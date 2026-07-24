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

import { FilterValueGeneric } from "./filter-value-generic";

/**
 * Defines a filterable property for a generic data type.
 */

export type FilterActionType = "add" | "remove" | "change" | "none";

export class FilterOption<T = unknown> {
  readonly key: string;
  readonly value: string | null;
  readonly label: string;
  readonly hint?: string;
  readonly matches: (item: T, filterValue: FilterValueGeneric<T>) => boolean;
  /**
   * Optional predicate used for keyword-less (free-text) search: returns true if the given search
   * term matches this column of the item. Columns that define it participate in global search, where
   * a bare term entered without a keyword matches an item if any column's globalMatches returns true.
   */
  readonly globalMatches?: (item: T, term: string) => boolean;
  readonly isSelected?: (filterValue: FilterValueGeneric<T>) => boolean;
  readonly getActionType?: (filterValue: FilterValueGeneric<T>) => FilterActionType;
  readonly toggle?: (filterValue: FilterValueGeneric<T>) => FilterValueGeneric<T>;

  constructor(args: {
    key: string;
    value?: string | null;
    label: string;
    hint?: string;
    matches: (item: T, filterValue: FilterValueGeneric<T>) => boolean;
    globalMatches?: (item: T, term: string) => boolean;
    isSelected?: (filterValue: FilterValueGeneric<T>) => boolean;
    getActionType?: (filterValue: FilterValueGeneric<T>) => FilterActionType;
    toggle?: (filterValue: FilterValueGeneric<T>) => FilterValueGeneric<T>;
  }) {
    this.key = args.key;
    this.value = args.value ?? null;
    this.label = args.label;
    this.hint = args.hint;
    this.matches = args.matches;
    this.globalMatches = args.globalMatches;
    this.isSelected = args.isSelected;
    this.getActionType = args.getActionType ?? ((filterValue) => (filterValue.hasKey(this.key) ? "remove" : "add"));
    this.toggle = args.toggle;
  }

  /**
   * Returns a new instance of the FilterOption with an updated value.
   */
  withValue(value: string | null): FilterOption<T> {
    return new FilterOption<T>({
      key: this.key,
      value: value,
      label: this.label,
      hint: this.hint,
      matches: this.matches,
      globalMatches: this.globalMatches,
      isSelected: this.isSelected,
      getActionType: this.getActionType,
      toggle: this.toggle
    });
  }
}

export class DummyFilterOption<T = unknown> extends FilterOption<T> {
  constructor(args: { key: string; value?: string | null }) {
    super({
      key: args.key,
      label: args.key,
      value: args.value ?? null,
      matches: () => true
    });
  }

  override withValue(value: string | null): DummyFilterOption<T> {
    return new DummyFilterOption<T>({
      key: this.key,
      value: value
    });
  }
}
