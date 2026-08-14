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
import { computed, signal, Signal } from "@angular/core";

export type TableStatus = "denied" | "loading" | "error" | "empty" | "filtered" | "ready";

export interface TableStateResource {
  hasValue(): boolean;
  error(): unknown;
  reload(): unknown;
}

export function isInitialLoad(resource: Pick<TableStateResource, "hasValue" | "error">): boolean {
  return !resource.hasValue() && resource.error() == null;
}

export interface TableStateOptions {
  readonly resource: TableStateResource;
  readonly count: () => number;
  readonly filterActive?: () => boolean;
  readonly allowed?: () => boolean;
  readonly resetFilter?: () => void;
}

/**
 * How long the first load is given before anything is drawn for it. A response that arrives inside
 * this window goes straight to the table or to the state panel, so neither is shown and taken away
 * again. The global progress bar covers the wait either way.
 */
export const FIRST_LOAD_GRACE_MS = 200;

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
      // Drawing a table of placeholder rows only to replace it with the empty panel a moment later
      // reads as a glitch, so the first load draws neither until it has taken long enough to be
      // worth reporting. The grace runs from construction, which is when that load starts.
      return status !== "loading" || this.firstLoadGraceElapsed();
    });

    setTimeout(() => this.firstLoadGraceElapsed.set(true), FIRST_LOAD_GRACE_MS);
  }

  /**
   * Whether a filter is narrowing the list right now. Read by the error panel: where the request
   * carries the filter, the filter is a candidate cause of the failure, and retrying the same
   * request cannot clear it.
   */
  readonly isFiltered: Signal<boolean>;

  /** False only for the opening moments of the first load; see FIRST_LOAD_GRACE_MS. */
  private readonly firstLoadGraceElapsed = signal(false);

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
