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
import { Injectable } from "@angular/core";

/** The requests in flight against one endpoint, collapsed into a single counted entry. */
export interface LoadingGroup {
  endpoint: string;
  count: number;
}

export interface LoadingServiceInterface {
  addListener(id: string, listener: (isLoading: boolean) => void): void;

  removeListener(id: string): void;

  notifyListeners(): void;

  addLoading(key: string, url: string): void;

  getLoadingGroups(): LoadingGroup[];

  clearAllLoadings(): void;

  isLoading(): boolean;

  removeLoading(key: string): void;
}

@Injectable({
  providedIn: "root"
})
export class LoadingService implements LoadingServiceInterface {
  listeners: Record<string, (isLoading: boolean) => void> = {};
  // A plain record, not a subscription of our own to the request: see the note on loadingInterceptor for why an
  // extra subscriber here would keep a cancelled request running.
  loadings: { key: string; url: string }[] = [];

  addListener(id: string, listener: (isLoading: boolean) => void): void {
    this.listeners[id] = listener;
  }

  removeListener(id: string): void {
    delete this.listeners[id];
  }

  notifyListeners(): void {
    Object.values(this.listeners).forEach((l) => l(this.isLoading()));
  }

  addLoading(key: string, url: string): void {
    this.loadings.push({ key, url });
    this.notifyListeners();
  }

  /** Grouped by the URL before the query string; ordered by the first request to each endpoint. */
  getLoadingGroups(): LoadingGroup[] {
    const groups = new Map<string, LoadingGroup>();
    this.loadings.forEach((loading) => {
      const endpoint = this.endpointOf(loading.url);
      const group = groups.get(endpoint);
      if (group) {
        group.count++;
      } else {
        groups.set(endpoint, { endpoint, count: 1 });
      }
    });
    return [...groups.values()];
  }

  clearAllLoadings(): void {
    // Forgets what is tracked; it cannot cancel the requests themselves any more, since tracking no longer holds a
    // subscription to one - see loadingInterceptor.
    this.loadings = [];
    this.notifyListeners();
  }

  isLoading(): boolean {
    return this.loadings.length > 0;
  }

  removeLoading(key: string): void {
    this.loadings = this.loadings.filter((l) => l.key !== key);
    this.notifyListeners();
  }

  private endpointOf(url: string): string {
    return url.split("?")[0];
  }
}
