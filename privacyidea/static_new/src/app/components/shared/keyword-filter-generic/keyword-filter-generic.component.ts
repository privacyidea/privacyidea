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
import { NgClass } from "@angular/common";
import { Component, inject, input, output, signal } from "@angular/core";
import { MatFabButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { FilterValueGeneric as GenericFilter } from "../../../core/models/filter_value_generic/filter_value_generic";
import { MatTooltip } from "@angular/material/tooltip";

/*
export class FilterKeyword {
  keyword: string;
  label: string;
  isSelected: (filterValue: FilterValueGeneric) => boolean;

  getIconName: (filterValue: FilterValueGeneric) => "remove_circle" | "add_circle" | "change_circle";
  toggleKeyword: (filterValue: FilterValueGeneric) => FilterValueGeneric;
  constructor(args: {
    key: string;
    label: string;
    isSelected?: (filterValue: FilterValueGeneric) => boolean;
    iconName?: (filterValue: FilterValueGeneric) => "remove_circle" | "add_circle" | "change_circle";
    toggle?: (filterValue: FilterValueGeneric) => FilterValueGeneric;
  }) {
    const { key, label, isSelected, iconName, toggle } = args;
    this.keyword = key;
    this.label = label;
    this.isSelected =
      isSelected ??
      ((filterValue: FilterValueGeneric) =>
        FilterKeyword.defaultIsSelected({
          keyword: this.keyword,
          filterValue: filterValue
        }));
    this.getIconName =
      iconName ??
      ((filterValue: FilterValueGeneric) =>
        FilterKeyword.defaultIconName({
          isSelected: this.isSelected,
          keyword: this.keyword,
          filterValue: filterValue
        }));
    this.toggleKeyword =
      toggle ??
      ((filterValue: FilterValueGeneric) =>
        FilterKeyword.defaultToggler({
          keyword: this.keyword,
          filterValue: filterValue
        }));
  }
  static defaultIsSelected(named: { keyword: string; filterValue: FilterValueGeneric }) {
    const { keyword, filterValue } = named;
    return filterValue.hasKey(keyword);
  }

  static defaultIconName(named: {
    isSelected?: (filterValue: FilterValueGeneric) => boolean;
    keyword: string;
    filterValue: FilterValueGeneric;
  }) {
    const { isSelected, keyword, filterValue } = named;
    const filterIsSelected = isSelected
      ? isSelected(filterValue)
      : FilterKeyword.defaultIsSelected({
          keyword: keyword,
          filterValue: filterValue
        });
    return filterIsSelected ? "remove_circle" : "add_circle";
  }

  static defaultToggler(named: { keyword: string; filterValue: FilterValueGeneric }): FilterValueGeneric {
    const { keyword, filterValue } = named;
    return filterValue.toggleKey(keyword);
  }

  static getValue(named: { keyword: string; filterValue: FilterValueGeneric }): string | null {
    const { keyword, filterValue } = named;
    return filterValue.getValueOfKey(keyword);
  }

  static toggleActive(filterValue: string): string {
    const activeRegex = /active:\s*(\S+)/i;
    const match = filterValue.match(activeRegex);

    if (!match) {
      return (filterValue.trim() + " active: true").trim();
    } else {
      const existingValue = match[1].toLowerCase();

      if (existingValue === "true") {
        return filterValue.replace(activeRegex, "active: false");
      } else if (existingValue === "false") {
        const removed = filterValue.replace(activeRegex, "").trim();
        return removed.replace(/\s{2,}/g, " ");
      } else {
        return filterValue.replace(activeRegex, "active: true");
      }
    }
  }
}
*/

export class FilterOption<T = any> {
  key: string;
  value: string | null;
  label: string;
  hint?: string;
  matches: (item: T, filterValue: GenericFilter<T>) => boolean;
  isSelected?: (filterValue: GenericFilter<T>) => boolean;
  getIconName?: (filterValue: GenericFilter<T>) => "remove_circle" | "add_circle" | "change_circle";
  toggleKeyword?: (filterValue: GenericFilter<T>) => GenericFilter<T>;

  constructor(args: {
    key: string;
    value?: string | null;
    label: string;
    hint?: string;
    matches: (item: T, filterValue: GenericFilter<T>) => boolean;
    isSelected?: (filterValue: GenericFilter<T>) => boolean;
    iconName?: (filterValue: GenericFilter<T>) => "remove_circle" | "add_circle" | "change_circle";
    toggle?: (filterValue: GenericFilter<T>) => GenericFilter<T>;
  }) {
    this.key = args.key;
    this.value = args.value ?? null;
    this.label = args.label;
    this.hint = args.hint;
    this.matches = args.matches;
    this.isSelected = args.isSelected;
    this.getIconName = args.iconName;
    this.toggleKeyword = args.toggle;
  }

  withValue(value: string | null): FilterOption<T> {
    return new FilterOption<T>({
      key: this.key,
      value: value,
      label: this.label,
      hint: this.hint,
      matches: this.matches,
      isSelected: this.isSelected,
      iconName: this.getIconName,
      toggle: this.toggleKeyword
    });
  }
}

export class DummyFilterOption extends FilterOption {
  isDummy = true;
  constructor(args: { key: string; value?: string | null }) {
    super({
      key: args.key,
      label: args.key,
      value: args.value ?? null,
      matches: () => true
    });
  }

  override withValue(value: string): FilterOption<any> {
    return new DummyFilterOption({ key: this.key, value: value });
  }
}

@Component({
  selector: "app-keyword-filter-generic",
  standalone: true,
  imports: [NgClass, MatIcon, MatFabButton, MatTooltip],
  templateUrl: "./keyword-filter-generic.component.html",
  styleUrl: "./keyword-filter-generic.component.scss"
})
export class KeywordFilterGenericComponent<T> {
  readonly filterOptions = input.required<FilterOption[]>();
  readonly advancedKeywordFilters = input<FilterOption[]>([]);
  readonly filterHTMLInputElement = input.required<HTMLInputElement>();
  readonly filter = input.required<GenericFilter<T>>();
  readonly filterChange = output<GenericFilter<T>>();
  showAdvancedFilter = signal(false);

  onKeywordClick(filterKeyword: FilterOption): void {
    this.toggleFilter(filterKeyword);
  }

  onToggleAdvancedFilter(): void {
    this.showAdvancedFilter.update((b) => !b);
  }

  // isFilterSelected(filter: string, inputValue: FilterValueGeneric): boolean {
  //   // return this.filterValue().isSelected(filterKeyword);
  // }

  getFilterIconName(filterKeyword: FilterOption): "remove_circle" | "add_circle" | "change_circle" {
    return this.filter().getFilterIconNameOf(filterKeyword);
  }

  toggleFilter(filterKeyword: FilterOption): void {
    const newFilterValue = this.filter().toggleFilterKeyword(filterKeyword);
    this.filterChange.emit(newFilterValue);
    // Focus the input element after changing the filter
    this.filterHTMLInputElement().focus();
  }

  filterIsEmpty(): boolean {
    return this.filter().isEmpty;
  }
}
