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
import { computed, linkedSignal, resource, ResourceRef, Signal, signal, WritableSignal } from "@angular/core";
import { PageEvent } from "@angular/material/paginator";
import { ApiClientServiceInterface, RememberedDevice, RememberedDevicesPage } from "./api-client.service";

const EMPTY_PAGE: RememberedDevicesPage = { devices: [], count: 0, prev: null, next: null };

export interface RememberedDevicesListOptions<Request> {
  readonly apiClientService: ApiClientServiceInterface;
  /** What the list shows, like the viewed client or user. The list goes back to its first page when it changes. */
  readonly scope: () => unknown;
  /** The request for the devices, or undefined to load none. */
  readonly request: () => Request | undefined;
  readonly load: (request: Request, page: { page: number; pageSize: number }) => Promise<RememberedDevicesPage>;
  readonly pageSize: number;
}

/**
 * One paged list of remembered devices: it loads the shown page and reloads it when the remembered devices change.
 * Create it in an injection context, like a field initializer of a component.
 */
export class RememberedDevicesList<Request> {
  readonly pageIndex: WritableSignal<number>;
  readonly pageSize: WritableSignal<number>;
  readonly resource: ResourceRef<RememberedDevicesPage | undefined>;
  readonly devices: Signal<RememberedDevice[]>;
  readonly count: Signal<number>;

  constructor(private readonly options: RememberedDevicesListOptions<Request>) {
    this.pageIndex = linkedSignal({ source: options.scope, computation: () => 0 });
    this.pageSize = signal<number>(options.pageSize);

    this.resource = resource({
      params: () => ({
        request: options.request(),
        page: this.pageIndex() + 1,
        pageSize: this.pageSize(),
        reloadTrigger: options.apiClientService.rememberedDevicesReloadTrigger()
      }),
      loader: ({ params }) => {
        if (!params.request) return Promise.resolve(EMPTY_PAGE);
        return options.load(params.request, { page: params.page, pageSize: params.pageSize });
      }
    });

    // Keeps the rows of the previous page while the next one loads, so the table does not empty in between
    const loadedPage = linkedSignal<
      { value: RememberedDevicesPage | undefined; isLoading: boolean; error: unknown },
      RememberedDevicesPage
    >({
      source: () => ({
        value: this.resource.hasValue() ? this.resource.value() : undefined,
        isLoading: this.resource.isLoading(),
        error: this.resource.error()
      }),
      computation: (source, previous) => {
        if (source.error) return EMPTY_PAGE;
        if (!source.value) return source.isLoading ? (previous?.value ?? EMPTY_PAGE) : EMPTY_PAGE;
        return source.value;
      }
    });

    this.devices = computed(() => loadedPage().devices);
    this.count = computed(() => loadedPage().count);
  }

  onPage(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  /** Shows the list again after one device of the shown page was revoked. */
  reloadAfterRevoke(): void {
    // The last device of a later page takes that page away
    if (this.pageIndex() > 0 && this.devices().length <= 1) {
      this.pageIndex.update((index) => index - 1);
      return;
    }
    this.options.apiClientService.reloadRememberedDevices();
  }

  /** Shows the first page again after several devices were revoked at once. */
  reloadFromFirstPage(): void {
    if (this.pageIndex() !== 0) {
      this.pageIndex.set(0);
      return;
    }
    this.options.apiClientService.reloadRememberedDevices();
  }
}
