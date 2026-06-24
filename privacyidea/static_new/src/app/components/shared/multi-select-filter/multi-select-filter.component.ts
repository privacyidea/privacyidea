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
import { Component, input, output } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatDividerModule } from "@angular/material/divider";
import { MatIcon } from "@angular/material/icon";
import { MatMenuModule } from "@angular/material/menu";
import { MatTooltipModule } from "@angular/material/tooltip";

/**
 * A reusable table-header filter control: a filter icon that opens a menu of checkbox-style options for selecting
 * multiple values at once (e.g. authentication-log event types or realms). The component is controlled — it renders
 * the `selected` input and emits the full next selection via `selectionChange`; the parent owns where the selection
 * is stored (typically a comma-separated filter value the API splits as CSV).
 */
@Component({
  selector: "app-multi-select-filter",
  standalone: true,
  imports: [MatButtonModule, MatIcon, MatMenuModule, MatDividerModule, MatTooltipModule],
  templateUrl: "./multi-select-filter.component.html",
  styleUrl: "./multi-select-filter.component.scss"
})
export class MultiSelectFilterComponent {
  readonly options = input.required<readonly string[]>();
  readonly selected = input<readonly string[]>([]);
  readonly label = input<string>("");
  readonly selectionChange = output<string[]>();

  isSelected(value: string): boolean {
    return this.selected().includes(value);
  }

  toggle(value: string): void {
    const current = this.selected();
    const next = current.includes(value) ? current.filter((entry) => entry !== value) : [...current, value];
    this.selectionChange.emit(next);
  }

  clear(): void {
    this.selectionChange.emit([]);
  }
}
