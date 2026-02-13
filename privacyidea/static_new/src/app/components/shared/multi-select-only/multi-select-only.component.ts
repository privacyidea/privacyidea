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

import { Component, input, output, computed } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule, MatSelectChange } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatIconModule } from "@angular/material/icon";

@Component({
  selector: "app-multi-select-only",
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, MatButtonModule, MatTooltipModule, MatIconModule],
  templateUrl: "./multi-select-only.component.html",
  styleUrls: ["./multi-select-only.component.scss"]
})
export class MultiSelectOnlyComponent {
  // Inputs
  readonly label = input<string>("");
  readonly items = input<string[] | Set<string>>([]);
  readonly selectedItems = input<string[]>([]);
  readonly tooltipText = input<string>("");

  // Outputs
  readonly selectionChange = output<string[]>();

  /**
   * Localized labels for the toggle action.
   */
  protected readonly toggleLabels = {
    select: $localize`Select all`,
    deselect: $localize`Deselect all`
  };

  /**
   * Normalizes input items to a unique array.
   */
  readonly uniqueItems = computed(() => {
    const source = this.items();
    const array = source instanceof Set ? Array.from(source) : source;
    return [...new Set(array)].sort();
  });

  /**
   * Disables the select if no items are available.
   */
  readonly isDisabled = computed(() => this.uniqueItems().length === 0);

  /**
   * Determines if all available unique items are currently selected.
   */
  readonly isAllSelected = computed(() => {
    const total = this.uniqueItems().length;
    return total > 0 && this.selectedItems().length === total;
  });

  /**
   * Pre-formats the string for the mat-select-trigger to keep the template clean.
   */
  readonly triggerValue = computed(() => this.selectedItems().join(", "));

  /**
   * Standard selection handler.
   */
  public onSelectionChange(event: MatSelectChange): void {
    this.selectionChange.emit(event.value);
  }

  /**
   * Deselects everything and selects ONLY the targeted item.
   */
  public selectOnly(event: MouseEvent, item: string): void {
    event.stopPropagation();
    this.selectionChange.emit([item]);
  }

  /**
   * Toggles a single item.
   */
  public toggle(item: string): void {
    const currentSelection = this.selectedItems();
    const isSelected = currentSelection.includes(item);
    const newSelection = isSelected
      ? currentSelection.filter((i) => i !== item) // Remove item
      : [...currentSelection, item]; // Add item

    this.selectionChange.emit(newSelection);
  }

  /**
   * Toggles between selecting all and none.
   */
  public toggleAll(): void {
    this.selectionChange.emit(this.isAllSelected() ? [] : this.uniqueItems());
  }
}
