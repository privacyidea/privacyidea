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
import { Signal, signal } from "@angular/core";

export type SortDirection = "asc" | "desc";
export type SortValue = string | number | boolean | null | undefined;

export interface TableSortState {
  readonly active: Signal<string | null>;
  readonly direction: Signal<SortDirection>;
  toggle(key: string): void;
}

export class TableSort<T, K extends string> implements TableSortState {
  readonly active = signal<K | null>(null);
  readonly direction = signal<SortDirection>("asc");

  constructor(private readonly accessors: Record<K, (row: T) => SortValue>) {}

  toggle(key: K): void {
    if (this.active() !== key) {
      this.active.set(key);
      this.direction.set("asc");
      return;
    }
    if (this.direction() === "asc") {
      this.direction.set("desc");
      return;
    }
    this.active.set(null);
    this.direction.set("asc");
  }

  apply(rows: T[]): T[] {
    const key = this.active();
    if (key === null) {
      return rows;
    }
    const accessor = this.accessors[key];
    const factor = this.direction() === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => compare(accessor(a), accessor(b), factor));
  }
}

function compare(a: SortValue, b: SortValue, factor: number): number {
  const aMissing = a === null || a === undefined;
  const bMissing = b === null || b === undefined;
  if (aMissing || bMissing) {
    return aMissing && bMissing ? 0 : aMissing ? 1 : -1;
  }
  if (typeof a === "number" && typeof b === "number") {
    return (a - b) * factor;
  }
  return String(a).localeCompare(String(b), undefined, { numeric: true }) * factor;
}
