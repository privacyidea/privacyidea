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
import { FilterValueGeneric } from "../../../core/models/filter_value_generic/filter_value_generic";

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

  static getValue(named: { keyword: string; filterValue: FilterValueGeneric }): string | undefined {
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

export class FilterKeyword {
  key: string;
  label: string;
  isSelected?: (filterValue: FilterValueGeneric) => boolean;
  getIconName?: (filterValue: FilterValueGeneric) => "remove_circle" | "add_circle" | "change_circle";
  toggleKeyword?: (filterValue: FilterValueGeneric) => FilterValueGeneric;

  constructor(args: {
    key: string;
    label: string;
    isSelected?: (filterValue: FilterValueGeneric) => boolean;
    iconName?: (filterValue: FilterValueGeneric) => "remove_circle" | "add_circle" | "change_circle";
    toggle?: (filterValue: FilterValueGeneric) => FilterValueGeneric;
  }) {
    this.key = args.key;
    this.label = args.label;
    this.isSelected = args.isSelected;
    this.getIconName = args.iconName;
    this.toggleKeyword = args.toggle;
  }
}

@Component({
  selector: "app-keyword-filter-generic",
  standalone: true,
  imports: [NgClass, MatIcon, MatFabButton],
  templateUrl: "./keyword-filter-generic.component.html",
  styleUrl: "./keyword-filter-generic.component.scss"
})
export class KeywordFilterGenericComponent {
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  readonly apiFilter = input.required<FilterKeyword[]>();
  readonly advancedApiFilter = input<FilterKeyword[]>([]);
  readonly filterHTMLInputElement = input.required<HTMLInputElement>();
  readonly filterValue = input.required<FilterValueGeneric>();
  readonly filterValueChange = output<FilterValueGeneric>();
  showAdvancedFilter = signal(false);

  onKeywordClick(filterKeyword: FilterKeyword): void {
    this.toggleFilter(filterKeyword);
  }

  onToggleAdvancedFilter(): void {
    this.showAdvancedFilter.update((b) => !b);
  }

  isFilterSelected(filter: string, inputValue: FilterValueGeneric): boolean {
    if (filter === "infokey & infovalue") {
      return inputValue.hasKey("infokey") || inputValue.hasKey("infovalue");
    }
    if (filter === "machineid & resolver") {
      return inputValue.hasKey("machineid") || inputValue.hasKey("resolver");
    }
    return inputValue.hasKey(filter);
  }

  getFilterIconName(filterKeyword: FilterKeyword): "remove_circle" | "add_circle" | "change_circle" {
    return this.filterValue().getFilterIconName(filterKeyword);
  }

  toggleFilter(filterKeyword: FilterKeyword): void {
    const newFilterValue = this.filterValue().toggleKey(filterKeyword);
    this.filterValueChange.emit(newFilterValue);
    // Focus the input element after changing the filter
    this.filterHTMLInputElement().focus();
  }

  filterIsEmpty(): boolean {
    return this.filterValue().isEmpty;
  }
}
