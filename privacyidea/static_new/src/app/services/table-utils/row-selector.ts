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
import { computed, linkedSignal, Signal } from "@angular/core";
import { toObservable, toSignal } from "@angular/core/rxjs-interop";
import { MatTableDataSource } from "@angular/material/table";
import { finalize, switchMap } from "rxjs";

/**
 * The rows a table currently renders: filtered, sorted and reduced to the current page.
 *
 * Follows the data source signal, disconnecting the previous one on every swap and on destroy.
 * Must be called in an injection context, e.g. as a field initializer.
 */
export function renderedRows<T>(dataSource: Signal<MatTableDataSource<T>>): Signal<readonly T[]> {
  return toSignal(
    toObservable(dataSource).pipe(switchMap((source) => source.connect().pipe(finalize(() => source.disconnect())))),
    { initialValue: [] as T[] }
  );
}

/**
 * Row selection of a table, scoped to the rows the table currently shows.
 *
 * Everything is derived from `visibleRows`, so a selection can never reach a row behind the filter or
 * on another page: selecting all selects what is on screen, and a row that leaves the screen loses its
 * tick. Rows are held by key, so reloading the same data keeps the selection.
 */
export class RowSelector<T> {
  /** The rows the table renders: filtered, sorted and reduced to the current page. */
  readonly visibleRows: Signal<readonly T[]>;

  private readonly selectedKeys = linkedSignal<readonly T[], Set<string>>({
    source: () => this.visibleRows(),
    computation: (rows, previous) => {
      const visible = new Set(rows.map(this.keyGetter));
      return new Set([...(previous?.value ?? [])].filter((selectedKey) => visible.has(selectedKey)));
    }
  });

  readonly selectedRows = computed(() =>
    this.visibleRows().filter((row) => this.selectedKeys().has(this.keyGetter(row)))
  );
  readonly selectedCount = computed(() => this.selectedRows().length);
  readonly hasSelection = computed(() => this.selectedCount() > 0);

  /** Whether the table shows any row at all, i.e. whether selecting is possible. */
  readonly hasVisibleRows = computed(() => this.visibleRows().length > 0);

  /** Whether every visible row is selected. False for an empty table. */
  readonly allRowsSelected = computed(
    () => this.hasVisibleRows() && this.visibleRows().every((row) => this.selectedKeys().has(this.keyGetter(row)))
  );

  /** Whether some, but not all, visible rows are selected. */
  readonly someRowsSelected = computed(() => this.hasSelection() && !this.allRowsSelected());

  private readonly keyGetter: (row: T) => string;

  constructor(args: { keyGetter: (row: T) => string; visibleRows: Signal<readonly T[]> }) {
    this.keyGetter = args.keyGetter;
    this.visibleRows = args.visibleRows;
  }

  isRowSelected(row: T): boolean {
    return this.selectedKeys().has(this.keyGetter(row));
  }

  selectRow(row: T): void {
    this.selectedKeys.update((current) => new Set(current).add(this.keyGetter(row)));
  }

  deselectRow(row: T): void {
    const rowKey = this.keyGetter(row);
    this.selectedKeys.update((current) => {
      const next = new Set(current);
      next.delete(rowKey);
      return next;
    });
  }

  setRowSelected(row: T, selected: boolean): void {
    if (selected) {
      this.selectRow(row);
    } else {
      this.deselectRow(row);
    }
  }

  selectAllRows(): void {
    this.selectedKeys.set(new Set(this.visibleRows().map(this.keyGetter)));
  }

  deselectAllRows(): void {
    this.selectedKeys.set(new Set());
  }
}
