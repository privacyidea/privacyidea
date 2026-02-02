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
import { Component, input, output, signal } from "@angular/core";
import { MatFabButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { FilterValueGeneric as GenericFilter } from "../../../core/models/filter_value_generic/filter_value_generic";
import { MatTooltip } from "@angular/material/tooltip";

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
