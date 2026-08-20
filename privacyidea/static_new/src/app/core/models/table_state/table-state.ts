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
import { computed, Signal } from "@angular/core";

export type TableStatus = "denied" | "loading" | "error" | "empty" | "filtered" | "ready";

export interface TableStateResource {
  hasValue(): boolean;
  error(): unknown;
  reload(): unknown;
}

export interface TableStateOptions {
  readonly resource: TableStateResource;
  readonly count: () => number;
  readonly filterActive?: () => boolean;
  readonly allowed?: () => boolean;
  readonly resetFilter?: () => void;
}

export class TableState {
  readonly status: Signal<TableStatus>;
  readonly rowStatus: Signal<TableStatus>;
  /**
   * False while a standalone state panel takes the place of the whole table area - filter, paginator,
   * actions and table alike - because nothing the user does to them brings rows back.
   * The filtered state keeps them, because the filter is what the user has to change to get rows back.
   */
  readonly showTable: Signal<boolean>;

  constructor(private readonly options: TableStateOptions) {
    this.status = computed(() => {
      if (this.options.allowed?.() === false) {
        return "denied";
      }
      if (this.options.resource.error() != null) {
        return "error";
      }
      if (!this.options.resource.hasValue()) {
        return "loading";
      }
      if (this.options.count() > 0) {
        return "ready";
      }
      return this.options.filterActive?.() ? "filtered" : "empty";
    });
    this.rowStatus = computed(() => (this.status() === "ready" ? "filtered" : this.status()));
    this.isFiltered = computed(() => this.options.filterActive?.() ?? false);
    this.showTable = computed(() => {
      const status = this.status();
      if (status === "empty" || status === "denied" || status === "error") {
        return false;
      }
      // A table of placeholder rows is shaped like data, so ending the load on the empty panel
      // reads as rows arriving and then being taken away. The panel speaks for the load as well,
      // which makes every outcome a change of its contents rather than a change of what is on screen.
      return status !== "loading";
    });
  }

  /**
   * Whether a filter is narrowing the list right now. Read by the error panel: where the request
   * carries the filter, the filter is a candidate cause of the failure, and retrying the same
   * request cannot clear it.
   */
  readonly isFiltered: Signal<boolean>;

  get canResetFilter(): boolean {
    return this.options.resetFilter !== undefined;
  }

  retry(): void {
    this.options.resource.reload();
  }

  resetFilter(): void {
    this.options.resetFilter?.();
  }
}
