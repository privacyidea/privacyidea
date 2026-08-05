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

export class TableState {
  readonly status: Signal<TableStatus>;
  readonly rowStatus: Signal<TableStatus>;

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
  }

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
