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
import { Component, computed, inject, linkedSignal, resource, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import {
  ApiClientService,
  ApiClientServiceInterface,
  RememberedDevice,
  RememberedDevicesPage
} from "@services/api-client/api-client.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";

const EMPTY_PAGE: RememberedDevicesPage = { devices: [], count: 0, prev: null, next: null };

/** The remembered devices of the user on the details page, on all API clients. */
@Component({
  selector: "app-user-details-remembered-devices",
  standalone: true,
  imports: [
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatPaginatorModule,
    DatePipe,
    TableStateComponent
  ],
  templateUrl: "./user-details-remembered-devices.component.html",
  styleUrl: "./user-details-remembered-devices.component.scss"
})
export class UserDetailsRememberedDevicesComponent {
  protected readonly apiClientService: ApiClientServiceInterface = inject(ApiClientService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly router = inject(Router);

  private readonly viewedUser = computed(() => ({
    user: this.userService.detailsUser().username,
    realm: this.userService.selectedUserRealm()
  }));

  // Back to the first page whenever another user is shown
  pageIndex = linkedSignal({ source: () => this.viewedUser(), computation: () => 0 });
  pageSize = signal<number>(10);
  pageSizeOptions = [10, 25, 50];

  displayedColumns = ["client", "ip_address", "user_agent", "created_at", "last_used_at", "expires_at", "actions"];

  readonly devicesResource = resource({
    params: () => ({
      ...this.viewedUser(),
      allowed: this.authService.actionAllowed("remembered_device_list"),
      page: this.pageIndex() + 1,
      pageSize: this.pageSize(),
      reloadTrigger: this.apiClientService.rememberedDevicesReloadTrigger()
    }),
    loader: ({ params }) => {
      if (!params.user || !params.realm || !params.allowed) return Promise.resolve(EMPTY_PAGE);
      return this.apiClientService.getUserRememberedDevices(params.user, params.realm, {
        page: params.page,
        pageSize: params.pageSize
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

  readonly tableState = new TableState({
    resource: this.devicesResource,
    count: () => this.count(),
    allowed: () => this.authService.actionAllowed("remembered_device_list")
  });

  goToClient(device: RememberedDevice): void {
    void this.router.navigateByUrl(ROUTE_PATHS.POLICIES_API_CLIENTS_DETAILS + device.client_id);
  }

  onPage(event: PageEvent): void {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  revokeDevice(device: RememberedDevice): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@apiClient.revokeRememberedDevice:Revoke Remembered Device`,
          items: [device.client_name ?? device.client_id],
          itemType: "remembered-device",
          confirmAction: { label: $localize`:@@token.revoke:Revoke`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService.revokeDevice(device.client_id, device.device_id).then(() => {
            // The last device of a later page takes that page away
            if (this.pageIndex() > 0 && this.devices().length <= 1) {
              this.pageIndex.update((index) => index - 1);
              return;
            }
            this.apiClientService.reloadRememberedDevices();
          });
        }
      });
  }

  revokeAll(): void {
    const { user, realm } = this.viewedUser();
    if (this.count() === 0 || !user || !realm) return;
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@user.revokeAllRememberedDevicesOfUser:Revoke All Remembered Devices of User`,
          items: [`${user}@${realm}`],
          itemType: "remembered-device",
          confirmAction: { label: $localize`:@@apiClient.revokeAll:Revoke All`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (!result) return;
        void this.apiClientService.revokeAllForUser(user, realm).then(() => {
          if (this.pageIndex() !== 0) {
            this.pageIndex.set(0);
            return;
          }
          this.apiClientService.reloadRememberedDevices();
        });
      });
  }
}
