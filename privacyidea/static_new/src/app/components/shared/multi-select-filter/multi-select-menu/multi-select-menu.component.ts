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
import { Component, ViewChild, computed, input, output } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatDividerModule } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { MatMenu, MatMenuModule } from "@angular/material/menu";

import { MultiSelectFilterOption } from "../multi-select-filter-option";

/**
 * The checkbox-style selection menu shared by {@link MultiSelectFilterComponent} (icon-button trigger in a table
 * header) and any other trigger that needs multi-select behaviour — e.g. a `mat-menu-item` that opens this as a
 * nested submenu via `[matMenuTriggerFor]="ref.matMenu"`.
 *
 * Controlled component: renders `selected` and emits the full next selection via `selectionChange`.
 */
@Component({
  selector: "app-multi-select-menu",
  standalone: true,
  imports: [MatButtonModule, MatIcon, MatMenuModule, MatDividerModule],
  templateUrl: "./multi-select-menu.component.html",
  styleUrl: "./multi-select-menu.component.scss"
})
export class MultiSelectMenuComponent {
  @ViewChild("menu", { static: true }) readonly matMenu!: MatMenu;

  readonly options = input.required<readonly (string | MultiSelectFilterOption)[]>();
  readonly selected = input<readonly string[]>([]);
  readonly valueSuffix = input<string>("");
  readonly allowCustom = input<boolean>(false);
  readonly selectionChange = output<string[]>();
  readonly addCustom = output<void>();

  readonly normalizedOptions = computed<MultiSelectFilterOption[]>(() =>
    this.options().map((option) => (typeof option === "string" ? { label: option, value: option } : option))
  );

  private storedValue(option: MultiSelectFilterOption): string {
    return option.value + this.valueSuffix();
  }

  isSelected(option: MultiSelectFilterOption): boolean {
    return this.selected().includes(this.storedValue(option));
  }

  toggle(option: MultiSelectFilterOption): void {
    const value = this.storedValue(option);
    const current = this.selected();
    const next = current.includes(value) ? current.filter((entry) => entry !== value) : [...current, value];
    this.selectionChange.emit(next);
  }

  clear(): void {
    this.selectionChange.emit([]);
  }

  onAddCustom(): void {
    this.addCustom.emit();
  }
}
