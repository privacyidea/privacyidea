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
import { Component, computed, inject, input, linkedSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatSelectModule } from "@angular/material/select";
import { MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { ApiClientService, ApiClientServiceInterface, RememberedDevice } from "@services/api-client/api-client.service";
import { RememberedDevicesList } from "@services/api-client/remembered-devices-list";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TooltipAriaLabelDirective } from "@components/shared/directives/tooltip-aria-label.directive";

@Component({
  selector: "app-api-client-remembered-devices",
  standalone: true,
  imports: [
    TooltipAriaLabelDirective,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatSelectModule,
    MatPaginatorModule,
    DatePipe,
    TableStateComponent
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
  realmFilter = linkedSignal({ source: () => this.clientId(), computation: () => "" });

  private readonly list = new RememberedDevicesList({
    apiClientService: this.apiClientService,
    scope: () => this.clientId(),
    request: () => {
      if (!this.clientId() || !this.authService.actionAllowed("remembered_device_list")) return undefined;
      return { clientId: this.clientId(), realm: this.realmFilter() || undefined };
    },
    load: ({ clientId, realm }, page) => this.apiClientService.getRememberedDevices(clientId, { ...page, realm }),
    pageSize: 50
  });

  pageIndex = this.list.pageIndex;
  pageSize = this.list.pageSize;
  pageSizeOptions = [10, 25, 50, 100];

  displayedColumns = ["user", "ip_address", "user_agent", "created_at", "last_used_at", "expires_at", "actions"];

  realmOptions = computed(() => this.realmService.realmOptions());

  readonly devices = this.list.devices;
  readonly count = this.list.count;

  readonly tableState = new TableState({
    resource: this.list.resource,
    count: () => this.count(),
    filterActive: () => !!this.realmFilter(),
    allowed: () => this.authService.actionAllowed("remembered_device_list"),
    resetFilter: () => this.onRealmFilterChange("")
  });

  userDevicesTooltip(): string {
    return $localize`:@@apiClient.revokeAllUserDevices:Revoke all of this user's remembered devices on this client`;
  }

  goToUser(device: RememberedDevice): void {
    if (!device.user) return;
    this.contentService.userSelected(device.user, device.realm);
  }

  onPage(event: PageEvent): void {
    this.list.onPage(event);
  }

  onRealmFilterChange(realm: string): void {
    this.realmFilter.set(realm);
    this.pageIndex.set(0);
  }

  revokeDevice(device: RememberedDevice): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@apiClient.revokeRememberedDevice:Revoke Remembered Device`,
          items: [device.device_id],
          itemType: "remembered-device",
          confirmAction: { label: $localize`:@@token.revoke:Revoke`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService.revokeDevice(this.clientId(), device.device_id).then(() => {
            this.list.reloadAfterRevoke();
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
          title: $localize`:@@apiClient.revokeAllDevicesForUser:Revoke All Devices for User`,
          items: [`${user}@${device.realm}`],
          itemType: "remembered-device",
          confirmAction: {
            label: $localize`:@@apiClient.revokeAllForThisClient:Revoke All for This Client`,
            value: true,
            type: "destruct"
          }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService
            .revokeAllForClient(this.clientId(), { realm: device.realm, user })
            .then(() => this.list.reloadFromFirstPage());
        }
      });
  }

  revokeAllLabel(): string {
    return this.realmFilter()
      ? $localize`:@@apiClient.revokeAllInThisRealm:Revoke All in This Realm`
      : $localize`:@@apiClient.revokeAll:Revoke All`;
  }

  revokeAll(): void {
    if (this.count() === 0) return;
    const realm = this.realmFilter();
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: realm
            ? $localize`:@@apiClient.revokeAllInRealm:Revoke All in Realm`
            : $localize`:@@apiClient.revokeAllRememberedDevices:Revoke All Remembered Devices`,
          items: [
            realm
              ? $localize`:@@apiClient.allDevicesForClientInRealm:All remembered devices for this client in realm ${realm}:REALM:`
              : $localize`:@@apiClient.allDevicesForClient:All remembered devices for this client`
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
          .then(() => this.list.reloadFromFirstPage());
      });
  }
}
