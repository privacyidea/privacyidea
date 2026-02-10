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

import { Component, Input, output, viewChild, ElementRef, signal } from "@angular/core";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { PolicyDetail } from "src/app/services/policies/policies.service";

@Component({
  selector: "app-policy-filter",
  standalone: true,
  imports: [MatInputModule, ClearableInputComponent],
  templateUrl: "./policy-filter.component.html",
  styleUrl: "./policy-filter.component.scss"
})
export class PolicyFilterComponent {
  /**
   * Classic @Input for initialization from parent.
   */
  @Input() set initialFilter(value: FilterValueGeneric<PolicyDetail>) {
    if (value) {
      this.updateFilterManually(value);
    }
  }

  @Input() unfilteredPolicies: PolicyDetail[] = [];

  readonly filterChange = output<FilterValueGeneric<PolicyDetail>>();
  readonly inputElement = viewChild.required<ElementRef<HTMLInputElement>>("filterHTMLInputElement");

  // Internal state for filtering logic
  readonly filter = signal<FilterValueGeneric<PolicyDetail>>(new FilterValueGeneric({ availableFilters: [] }));
  readonly isEmpty = signal(true);

  // The raw string bound to the input [value]
  public lastFilter: FilterValueGeneric<PolicyDetail> | null = null;

  /**
   * Manually updates the filter state.
   * Uses a guard to prevent redundant signal updates and DOM jitter.
   */
  public updateFilterManually(newFilter: FilterValueGeneric<PolicyDetail>): void {
    // Use strict comparison on trimmed strings to avoid ghost updates
    if (
      this.lastFilter?.rawValue.trim() !== newFilter.rawValue.trim() ||
      this.lastFilter?.availableFilters !== newFilter.availableFilters ||
      this.lastFilter?.apiFilterString !== newFilter.apiFilterString
    ) {
      this.filter.set(newFilter);
      this.isEmpty.set(newFilter.rawValue.trim() === "");
      this.lastFilter = newFilter;
    }
  }

  /**
   * Resets the filter and notifies the parent.
   */
  public clearFilter(): void {
    const empty = this.filter().clear();
    this.filter.set(empty);
    this.isEmpty.set(true);
    this.lastFilter = empty;
    this.inputElement().nativeElement.value = "";
    this.filterChange.emit(empty);
    this.focusInput();
  }

  /**
   * Synchronizes UI input with the model.
   * Only updates the bound 'rawValue' if the parser actively modified the text.
   */
  public onFilterChange(event: Event): void {
    const inputEl = event.target as HTMLInputElement;
    const currentText = inputEl.value;

    if (currentText === undefined) return;
    this.isEmpty.set(currentText === "");

    const updatedFilter = this.filter().setByString(currentText);

    // Only force a [value] update if the parser corrected the input (e.g., duplicates)
    this.lastFilter = updatedFilter;
    this.filterChange.emit(updatedFilter);
  }

  /**
   * Restores focus to the native input element.
   */
  public focusInput(): void {
    this.inputElement().nativeElement.focus();
  }
}
