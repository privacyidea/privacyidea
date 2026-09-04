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
import { Component, computed, ElementRef, inject, signal, untracked, ViewChild, viewChild } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ApiClientIssuedKeyBannerComponent } from "@components/policies/api-clients/api-client-issued-key-banner/api-client-issued-key-banner.component";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { ApiClient, ApiClientService, ApiClientServiceInterface } from "@services/api-client/api-client.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { IntegrationsService, IntegrationsServiceInterface } from "@services/integrations/integrations.service";
import { renderedRows, RowSelector } from "@services/table-utils/row-selector";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

@Component({
  selector: "app-api-clients",
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginator,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatTooltipModule,
    ScrollToTopDirective,
    MatFormField,
    MatLabel,
    ClearableInputComponent,
    MatInput,
    CopyableComponent,
    ApiClientIssuedKeyBannerComponent,
    DatePipe,
    TableStateComponent
  ],
  templateUrl: "./api-clients.component.html",
  styleUrl: "./api-clients.component.scss"
})
export class ApiClientsComponent {
  protected readonly apiClientService: ApiClientServiceInterface = inject(ApiClientService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly integrationsService: IntegrationsServiceInterface = inject(IntegrationsService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private readonly router = inject(Router);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  readonly tableState = new TableState({
    resource: this.apiClientService.apiClientResource,
    count: () => this.apiClientService.apiClients().length,
    allowed: () => this.authService.actionAllowed("api_client_list"),
    resetFilter: () => this.resetFilter()
  });

  readonly paginator = viewChild(MatPaginator);
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  displayedColumns: string[] = [
    "select",
    "display_name",
    "client_type",
    "status",
    "key_id",
    "created_at",
    "last_used_at",
    "actions"
  ];

  apiClientDataSource = computed(() => {
    const clients = this.apiClientService.apiClients();
    const dataSource = new MatTableDataSource(clients);
    dataSource.paginator = this.paginator() ?? null;
    dataSource.sort = this.sort;
    dataSource.filter = untracked(() => this.filterString()).toLowerCase();
    return dataSource;
  });

  selector = new RowSelector<ApiClient>({
    keyGetter: (client) => client.id,
    visibleRows: renderedRows(this.apiClientDataSource)
  });

  clientTypeLabel(clientType: string): string {
    return this.integrationsService.labelFor(clientType);
  }

  onCreateNewApiClient(): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_API_CLIENTS_NEW);
  }

  onEditApiClient(client: ApiClient): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_API_CLIENTS_DETAILS + client.id);
  }

  rotateKey(client: ApiClient): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@apiClient.rotateApiKey:Rotate API Key`,
          items: [client.display_name],
          itemType: "api-client",
          confirmAction: {
            label: $localize`:@@apiClient.rotateKey:Rotate key`,
            value: true,
            type: "destruct"
          }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService.rotateClient(client.id, client.display_name).catch(() => undefined);
        }
      });
  }

  deleteClient(client: ApiClient): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@apiClient.deleteApiClient:Delete API Client`,
          items: [client.display_name],
          itemType: "api-client",
          confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          void this.apiClientService.deleteClient(client.id).catch(() => undefined);
        }
      });
  }

  deleteSelected(): void {
    const selected = this.selector.selectedRows();
    if (selected.length === 0) {
      return;
    }
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@apiClient.deleteApiClients:Delete API Clients`,
          items: selected.map((row) => row.display_name),
          itemType: "api-client",
          confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          selected.forEach((row) => void this.apiClientService.deleteClient(row.id).catch(() => undefined));
          this.selector.deselectAllRows();
        }
      });
  }

  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);

    const ds = this.apiClientDataSource();
    ds.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.apiClientDataSource();
    ds.filter = "";
    const inputEl = this.filterInput?.nativeElement as HTMLInputElement | undefined;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}
