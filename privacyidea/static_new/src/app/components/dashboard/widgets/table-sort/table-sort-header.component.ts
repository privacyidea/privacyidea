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
import { Component, computed, input } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { TableSortState } from "@components/dashboard/widgets/table-sort/table-sort";
import { TruncationTooltipDirective } from "@components/shared/directives/truncation-tooltip.directive";

@Component({
  selector: "app-table-sort-header",
  standalone: true,
  imports: [MatIconButton, MatIcon, MatTooltip, TruncationTooltipDirective],
  templateUrl: "./table-sort-header.component.html",
  styleUrl: "./table-sort-header.component.scss"
})
export class TableSortHeaderComponent {
  readonly key = input.required<string>();
  readonly sortState = input.required<TableSortState>();
  readonly label = input.required<string>();
  readonly hasHintTooltip = input(false);

  protected readonly icon = computed<string>(() => {
    if (this.sortState().active() !== this.key()) {
      return "unfold_more";
    }
    return this.sortState().direction() === "asc" ? "keyboard_arrow_upward" : "keyboard_arrow_downward";
  });

  protected toggle(): void {
    this.sortState().toggle(this.key());
  }
}
