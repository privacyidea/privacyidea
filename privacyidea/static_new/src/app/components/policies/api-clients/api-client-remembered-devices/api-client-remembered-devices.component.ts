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
import { DatePipe } from "@angular/common";
import { Component, computed, inject, input, linkedSignal, resource, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatSelectModule } from "@angular/material/select";
import { MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import {
  ApiClientService,
  ApiClientServiceInterface,
  RememberedDevice,
  RememberedDevicesPage
} from "@services/api-client/api-client.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";

const EMPTY_PAGE: RememberedDevicesPage = { devices: [], count: 0, prev: null, next: null };

@Component({
  selector: "app-api-client-remembered-devices",
  standalone: true,
  imports: [
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatSelectModule,
    MatPaginatorModule,
    DatePipe
  ],
  templateUrl: "./api-client-remembered-devices.component.html",
  styleUrl: "./api-client-remembered-devices.component.scss"
})
export class ApiClientRememberedDevicesComponent {
  protected readonly apiClientService: ApiClientServiceInterface = inject(ApiClientService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);

  clientId = input.required<string>();

  // Reset to the first page / no realm filter whenever the viewed client changes,
  // so a stale page number or realm from a previous client (e.g. the router reusing
  // this instance across a same-route client-to-client navigation) can't carry over.
  pageIndex = linkedSignal({ source: () => this.clientId(), computation: () => 0 });
  pageSize = signal<number>(50);
  pageSizeOptions = [10, 25, 50, 100];
  realmFilter = linkedSignal({ source: () => this.clientId(), computation: () => "" });

  displayedColumns = ["user", "ip_address", "user_agent", "created_at", "last_used_at", "expires_at", "actions"];

  realmOptions = computed(() => this.realmService.realmOptions());

  readonly devicesResource = resource({
    params: () => ({
      clientId: this.clientId(),
      allowed: this.authService.actionAllowed("remembered_device_list"),
      page: this.pageIndex() + 1,
      pageSize: this.pageSize(),
      realm: this.realmFilter() || undefined,
      reloadTrigger: this.apiClientService.rememberedDevicesReloadTrigger()
    }),
    loader: ({ params }) => {
      if (!params.clientId || !params.allowed) return Promise.resolve(EMPTY_PAGE);
      return this.apiClientService.getRememberedDevices(params.clientId, {
        page: params.page,
        pageSize: params.pageSize,
        realm: params.realm
      });
    }
  });

  private readonly loadedPage = linkedSignal<
    { value: RememberedDevicesPage | undefined; isLoading: boolean; error: unknown },
    RememberedDevicesPage
  >({
    source: () => ({
      value: this.devicesResource.hasValue() ? this.devicesResource.value() : undefined,
      isLoading: this.devicesResource.isLoading(),
      error: this.devicesResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return EMPTY_PAGE;
      if (!source.value) return source.isLoading ? (previous?.value ?? EMPTY_PAGE) : EMPTY_PAGE;
      return source.value;
    }
  });

  readonly devices = computed<RememberedDevice[]>(() => this.loadedPage().devices);
  readonly count = computed<number>(() => this.loadedPage().count);
  readonly loadFailed = computed<boolean>(() => this.devicesResource.error() !== undefined);
  readonly isLoading = computed<boolean>(() => this.devicesResource.isLoading());

  userDevicesTooltip(): string {
    return $localize`Revoke all of this user's remembered devices on this client`;
  }

  goToUser(device: RememberedDevice): void {
    if (!device.user) return;
    this.contentService.userSelected(device.user, device.realm);
  }

  onPage(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onRealmFilterChange(realm: string): void {
    this.realmFilter.set(realm);
    this.pageIndex.set(0);
  }

  private reloadAfterRevoke(removedFromPage: number): void {
    if (this.pageIndex() > 0 && this.devices().length <= removedFromPage) {
      this.pageIndex.update((index) => index - 1);
      return;
    }
    this.apiClientService.reloadRememberedDevices();
  }

  private reloadFromFirstPage(): void {
    if (this.pageIndex() !== 0) {
      this.pageIndex.set(0);
      return;
    }
    this.apiClientService.reloadRememberedDevices();
  }

  revokeDevice(device: RememberedDevice): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Revoke Remembered Device`,
          items: [device.device_id],
          itemType: "remembered-device",
          confirmAction: { label: $localize`Revoke`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService.revokeDevice(this.clientId(), device.device_id).then(() => {
            this.reloadAfterRevoke(1);
          });
        }
      });
  }

  // One user can hold several remembered devices on the same client (one per
  // browser/device they logged in from), so this revokes every one of them -
  // still only on the client being viewed.
  revokeAllForUser(device: RememberedDevice): void {
    if (!device.user) return;
    const user = device.user;
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Revoke All Devices For User`,
          items: [`${user}@${device.realm}`],
          itemType: "remembered-device",
          confirmAction: { label: $localize`Revoke all for this client`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService
            .revokeAllForClient(this.clientId(), { realm: device.realm, user })
            .then(() => this.reloadFromFirstPage());
        }
      });
  }

  revokeAllLabel(): string {
    return this.realmFilter() ? $localize`Revoke all in this realm` : $localize`Revoke all`;
  }

  revokeAll(): void {
    if (this.count() === 0) return;
    const realm = this.realmFilter();
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: realm ? $localize`Revoke All In Realm` : $localize`Revoke All Remembered Devices`,
          items: [
            realm
              ? $localize`All remembered devices for this client in realm ${realm}`
              : $localize`All remembered devices for this client`
          ],
          itemType: "remembered-device",
          confirmAction: { label: this.revokeAllLabel(), value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (!result) return;
        void this.apiClientService
          .revokeAllForClient(this.clientId(), { realm: realm || undefined })
          .then(() => this.reloadFromFirstPage());
      });
  }
}
