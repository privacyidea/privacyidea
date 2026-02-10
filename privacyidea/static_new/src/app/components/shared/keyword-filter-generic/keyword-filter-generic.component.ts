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

import { NgClass } from "@angular/common";
import { Component, input, output, signal } from "@angular/core";
import { MatFabButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { FilterValueGeneric } from "../../../core/models/filter_value_generic/filter-value-generic";
import { FilterOption } from "src/app/core/models/filter_value_generic/filter-option";

@Component({
  selector: "app-keyword-filter-generic",
  standalone: true,
  imports: [NgClass, MatIcon, MatFabButton, MatTooltip],
  templateUrl: "./keyword-filter-generic.component.html",
  styleUrl: "./keyword-filter-generic.component.scss"
})
export class KeywordFilterGenericComponent<T> {
  readonly filterOptions = input.required<FilterOption<T>[]>();
  readonly advancedKeywordFilters = input<FilterOption<T>[]>([]);
  readonly filterHTMLInputElement = input.required<HTMLInputElement>();
  readonly filter = input.required<FilterValueGeneric<T>>();

  readonly filterChange = output<FilterValueGeneric<T>>();

  showAdvancedFilter = signal(false);

  /**
   * Toggles a filter key and ensures the input retains focus.
   */
  public onKeywordClick(filterOption: FilterOption<T>): void {
    const nextFilter = this.filter().toggleKey(filterOption.key);
    this.filterChange.emit(nextFilter);
    this.filterHTMLInputElement().focus();
  }

  public onToggleAdvancedFilter(): void {
    this.showAdvancedFilter.update((v) => !v);
  }

  public getFilterIconName(filterOption: FilterOption<T>): string {
    return this.filter().getFilterIconNameOf(filterOption);
  }

  public getFilterIconClass(option: FilterOption<T>): Record<string, boolean> {
    const icon = this.getFilterIconName(option);
    return {
      "change-keyword": icon === "change_circle",
      "remove-keyword": icon === "remove_circle",
      "add-keyword": icon === "add_circle"
    };
  }

  public filterIsEmpty(): boolean {
    return this.filter().isEmpty;
  }
}
