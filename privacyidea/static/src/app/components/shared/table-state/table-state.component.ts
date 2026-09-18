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
import { afterNextRender, Component, computed, ElementRef, inject, input, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { TableState, TableStatus } from "@core/models/table_state/table-state";

@Component({
  selector: "app-table-state",
  standalone: true,
  imports: [MatIconModule, MatButtonModule, MatProgressSpinnerModule],
  templateUrl: "./table-state.component.html",
  styleUrl: "./table-state.component.scss"
})
export class TableStateComponent {
  readonly table = input.required<TableState>();
  readonly status = input<TableStatus | undefined>(undefined);
  readonly icon = input<string>("");
  readonly heading = input<string>("");
  readonly hint = input<string>("");

  private readonly host = inject(ElementRef<HTMLElement>);
  // mat-progress-spinner's diameter is a numeric input, not something the ready-state icon's
  // font-size: var(--table-state-icon-size) approach can reach - so it stayed a fixed 40 whatever
  // scale the panel was set to, undersized next to the much bigger frame a page-scale table
  // (table.page-table-state-size) gives it. Read the same --table-state-icon-size the icon uses,
  // once after first render, so the spinner matches the icon that will replace it.
  protected readonly spinnerDiameter = signal(40);

  constructor() {
    afterNextRender(() => {
      const size = parseFloat(getComputedStyle(this.host.nativeElement).getPropertyValue("--table-state-icon-size"));
      if (size > 0) {
        this.spinnerDiameter.set(size);
      }
    });
  }

  /** Every state but `empty` names its own glyph; `empty` is domain-specific, so the call site supplies it. */
  private static readonly STATUS_ICONS: Partial<Record<TableStatus, string>> = {
    filtered: "search_off",
    error: "error_outline",
    cancelled: "update_disabled",
    denied: "lock"
  };

  readonly currentStatus = computed(() => this.status() ?? this.table().status());
  /** The panel says nothing while the request is still out; the global progress bar reports that. */
  readonly isLoading = computed(() => this.currentStatus() === "loading");
  readonly resolvedIcon = computed(() => TableStateComponent.STATUS_ICONS[this.currentStatus()] ?? this.icon());
  /** The projected call to action stays available where the list is empty for good, not where it failed or was filtered away. */
  readonly showsProjectedAction = computed(
    () => this.currentStatus() === "empty" || this.currentStatus() === "denied" || this.currentStatus() === "cancelled"
  );
}
