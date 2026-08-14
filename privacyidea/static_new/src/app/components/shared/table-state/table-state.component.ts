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
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { TableState, TableStatus } from "@core/models/table_state/table-state";

@Component({
  selector: "app-table-state",
  standalone: true,
  imports: [MatIconModule, MatButtonModule],
  host: { "[class.table-state-idle]": "isLoading()" },
  templateUrl: "./table-state.component.html",
  styleUrl: "./table-state.component.scss"
})
export class TableStateComponent {
  readonly table = input.required<TableState>();
  readonly status = input<TableStatus | undefined>(undefined);
  readonly icon = input<string>("");
  readonly heading = input<string>("");
  readonly hint = input<string>("");

  /** Every state but `empty` names its own glyph; `empty` is domain-specific, so the call site supplies it. */
  private static readonly STATUS_ICONS: Partial<Record<TableStatus, string>> = {
    filtered: "search_off",
    error: "error_outline",
    denied: "lock"
  };

  readonly currentStatus = computed(() => this.status() ?? this.table().status());
  /** The panel says nothing while the request is still out; the global progress bar reports that. */
  readonly isLoading = computed(() => this.currentStatus() === "loading");
  readonly resolvedIcon = computed(() => TableStateComponent.STATUS_ICONS[this.currentStatus()] ?? this.icon());
  /** The projected call to action stays available where the list is empty for good, not where it failed or was filtered away. */
  readonly showsProjectedAction = computed(() => this.currentStatus() === "empty" || this.currentStatus() === "denied");
}
