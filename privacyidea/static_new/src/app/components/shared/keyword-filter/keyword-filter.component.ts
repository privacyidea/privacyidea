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
import { Component, inject, Input, signal, WritableSignal } from "@angular/core";
import { MatFabButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { FilterValue } from "../../../core/models/filter_value";

@Component({
  selector: "app-keyword-filter",
  standalone: true,
  imports: [NgClass, MatIcon, MatFabButton],
  templateUrl: "./keyword-filter.component.html",
  styleUrl: "./keyword-filter.component.scss"
})
export class KeywordFilterComponent {
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  @Input() apiFilter: string[] = [];
  @Input() advancedApiFilter: string[] = [];
  @Input({ required: true }) filterHTMLInputElement!: HTMLInputElement;
  @Input({ required: true }) filterValue!: WritableSignal<FilterValue>;
  showAdvancedFilter = signal(false);

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
  }

  onToggleAdvancedFilter(): void {
    this.showAdvancedFilter.update((b) => !b);
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    if (filter === "infokey & infovalue") {
      return inputValue.hasKey("infokey") || inputValue.hasKey("infovalue");
    }
    if (filter === "machineid & resolver") {
      return inputValue.hasKey("machineid") || inputValue.hasKey("resolver");
    }
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "active" || keyword === "assigned" || keyword === "success") {
      const value = this.filterValue()?.getValueOfKey(keyword)?.toLowerCase();
      if (!value) {
        return "add_circle";
      }
      return value === "true" ? "change_circle" : value === "false" ? "remove_circle" : "add_circle";
    } else {
      const isSelected = this.isFilterSelected(keyword, this.filterValue());
      return isSelected ? "remove_circle" : "add_circle";
    }
  }

  toggleFilter(filterKeyword: string): void {
    let newValue;
    if (filterKeyword === "active" || filterKeyword === "assigned" || filterKeyword === "success") {
      newValue = this.tableUtilsService.toggleBooleanInFilter({
        keyword: filterKeyword,
        currentValue: this.filterValue()
      });
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: this.filterValue()
      });
    }
    this.filterValue.set(newValue);
    this.filterHTMLInputElement.focus();
  }

  filterIsEmpty(): boolean {
    const current = this.filterValue?.() ?? {};
    return current.value === "";
  }
}
