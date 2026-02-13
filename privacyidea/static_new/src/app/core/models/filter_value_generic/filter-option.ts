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
export class FilterOption<T = any> {
  readonly key: string;
  readonly value: string | null;
  readonly label: string;
  readonly hint?: string;
  readonly matches: (item: T, filterValue: FilterValueGeneric<T>) => boolean;
  readonly isSelected?: (filterValue: FilterValueGeneric<T>) => boolean;
  readonly getIconName?: (filterValue: FilterValueGeneric<T>) => string;
  readonly toggle?: (filterValue: FilterValueGeneric<T>) => FilterValueGeneric<T>;

  constructor(args: {
    key: string;
    value?: string | null;
    label: string;
    hint?: string;
    matches: (item: T, filterValue: FilterValueGeneric<T>) => boolean;
    isSelected?: (filterValue: FilterValueGeneric<T>) => boolean;
    iconName?: (filterValue: FilterValueGeneric<T>) => string;
    toggle?: (filterValue: FilterValueGeneric<T>) => FilterValueGeneric<T>;
  }) {
    this.key = args.key;
    this.value = args.value ?? null;
    this.label = args.label;
    this.hint = args.hint;
    this.matches = args.matches;
    this.isSelected = args.isSelected;
    this.getIconName = args.iconName;
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
      isSelected: this.isSelected,
      iconName: this.getIconName,
      toggle: this.toggle
    });
  }
}

export class DummyFilterOption<T = any> extends FilterOption<T> {
  readonly isDummy = true;

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
