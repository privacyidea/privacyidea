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
import { computed, Signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { Debouncer } from "@utils/debounce.utils";
import { buildFilterParams, filterParamsEqual } from "@utils/filter.utils";

/** Structural type of the base service, for mocks and injection tokens. */
export type FilterableTableServiceInterface = Pick<FilterableTableService, keyof FilterableTableService>;

/**
 * Filter and pagination behaviour shared by the services behind the paginated tables.
 *
 * A service supplies its own filter signal, its keyword list and its pagination state;
 * everything derived from those comes from here. Services whose backend needs more than
 * the plain allow-list override `filterParams`, those that map input differently
 * override `handleFilterInput`.
 */
export abstract class FilterableTableService {
  /**
   * The applied filter, i.e. the one the list request is built from. Usually a
   * `linkedSignal` that resets on navigation. Read `filterDraft` instead wherever the
   * filter input is displayed, so the view stays live while the debouncer waits.
   */
  abstract readonly activeFilter: WritableSignal<FilterValue>;

  private _filterDebouncer: Debouncer<FilterValue> | undefined;

  /**
   * Delays typed input. Built on the first read, because `activeFilter` is only
   * assigned once the constructor of the service that owns it ran.
   */
  get filterDebouncer(): Debouncer<FilterValue> {
    return (this._filterDebouncer ??= new Debouncer<FilterValue>(this.activeFilter));
  }

  /** Filter keywords the backend accepts and the filter input offers. */
  abstract readonly apiFilterKeys: string[];

  abstract pageIndex: WritableSignal<number>;
  abstract pageSize: WritableSignal<number>;
  abstract sort: WritableSignal<Sort>;

  /** Keywords offered behind the "advanced" toggle of the filter input. */
  readonly advancedApiFilterKeys: string[] = [];

  /** Keywords the backend accepts but that are never offered as a keyword. */
  readonly hiddenApiFilterKeys: string[] = [];

  /** Table column key to filter keyword, for the filter buttons in the column headers. */
  readonly apiFilterKeyMap: Record<string, string> = {};

  /** Keywords the backend matches exactly, i.e. that must not be wrapped in wildcards. */
  readonly exactMatchKeys = new Set<string>();

  readonly allFilterKeys: Signal<string[]> = computed(() => [
    ...this.apiFilterKeys,
    ...this.advancedApiFilterKeys,
    ...this.hiddenApiFilterKeys
  ]);

  /**
   * The value the user sees: the not yet applied input while typing, the applied filter
   * otherwise.
   */
  readonly filterDraft: Signal<FilterValue> = computed(() => this.filterDebouncer.draft());

  /** The query parameters the list resource is built from. */
  readonly filterParams: Signal<Record<string, string>> = computed(
    () => buildFilterParams(this.activeFilter().filterMap, this.allFilterKeys(), this.exactMatchKeys),
    { equal: filterParamsEqual }
  );

  /**
   * Clears what the user typed. Hidden entries survive, because they are not the user's
   * input but the scope the route put on the list.
   */
  clearFilter(): void {
    this.setFilter(this.activeFilter().copyWith({ value: "" }));
  }

  setFilter(filter: FilterValue): void {
    this.filterDebouncer.set(filter);
  }

  updateFilter(computeFilter: (current: FilterValue) => FilterValue): void {
    this.filterDebouncer.update(computeFilter);
  }

  /** The filter a keystroke in the filter input produces. */
  filterFromInput($event: Event): FilterValue {
    const input = $event.target as HTMLInputElement;
    return this.activeFilter().copyWith({ value: input.value });
  }

  /** Typed input, applied once the user stopped typing. */
  handleFilterInput($event: Event): void {
    this.filterDebouncer.schedule(this.filterFromInput($event));
  }

  /** Typed input, applied at once - for the enter key, which skips the delay. */
  applyFilterInput($event: Event): void {
    this.setFilter(this.filterFromInput($event));
  }
}
