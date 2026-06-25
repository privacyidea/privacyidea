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
import { Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { finalize, Observable, Subscription, take } from "rxjs";

export interface DashboardDataRef<T> {
  readonly value: Signal<T | undefined>;
  readonly revalidating: Signal<boolean>;
  readonly error: Signal<boolean>;
}

interface CacheEntry<T> {
  value: WritableSignal<T | undefined>;
  revalidating: WritableSignal<boolean>;
  error: WritableSignal<boolean>;
  inFlight: boolean;
  subscription?: Subscription;
}

export interface DashboardDataStoreInterface {
  load<T>(key: string, factory: () => Observable<T>): DashboardDataRef<T>;

  invalidate(key?: string): void;
}

@Injectable({ providedIn: "root" })
export class DashboardDataStore implements DashboardDataStoreInterface {
  private readonly entries = new Map<string, CacheEntry<unknown>>();

  load<T>(key: string, factory: () => Observable<T>): DashboardDataRef<T> {
    const entry = this.entryFor<T>(key);
    if (!entry.inFlight) {
      entry.inFlight = true;
      entry.error.set(false);
      entry.revalidating.set(true);
      entry.subscription = factory()
        .pipe(
          take(1),
          finalize(() => {
            entry.revalidating.set(false);
            entry.inFlight = false;
            entry.subscription = undefined;
          })
        )
        .subscribe({
          next: (value) => entry.value.set(value),
          error: () => entry.error.set(true)
        });
    }
    return entry;
  }

  invalidate(key?: string): void {
    if (key) {
      this.entries.get(key)?.subscription?.unsubscribe();
      this.entries.delete(key);
    } else {
      this.entries.forEach((entry) => entry.subscription?.unsubscribe());
      this.entries.clear();
    }
  }

  private entryFor<T>(key: string): CacheEntry<T> {
    let entry = this.entries.get(key) as CacheEntry<T> | undefined;
    if (!entry) {
      entry = {
        value: signal<T | undefined>(undefined),
        revalidating: signal(false),
        error: signal(false),
        inFlight: false
      };
      this.entries.set(key, entry as CacheEntry<unknown>);
    }
    return entry;
  }
}
