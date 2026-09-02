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

import { Component, computed, ElementRef, inject, signal, ViewChild, viewChild, WritableSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  RadiusServer,
  RadiusServerService,
  RadiusServerServiceInterface
} from "@services/radius-server/radius-server.service";

import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { renderedRows, RowSelector } from "@services/table-utils/row-selector";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

@Component({
  selector: "app-radius-servers",
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
    TableStateComponent
  ],
  templateUrl: "./radius-servers.component.html",
  styleUrl: "./radius-servers.component.scss"
})
export class RadiusServersComponent {
  protected readonly radiusService: RadiusServerServiceInterface = inject(RadiusServerService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly router = inject(Router);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength: WritableSignal<number> = computed(
    () => this.radiusService.radiusServers().length
  ) as WritableSignal<number>;
  readonly tableState = new TableState({
    resource: this.radiusService.radiusServerResource,
    count: () => this.radiusService.radiusServers().length,
    allowed: () => this.authService.actionAllowed("radiusserver_read"),
    resetFilter: () => this.resetFilter()
  });

  readonly paginator = viewChild(MatPaginator);
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef;

  displayedColumns: string[] = ["select", "identifier", "server", "dictionary", "description"];

  radiusDataSource = computed(() => {
    const servers = this.radiusService.radiusServers();
    const dataSource = new MatTableDataSource(servers);
    dataSource.paginator = this.paginator() ?? null;
    dataSource.sort = this.sort;
    return dataSource;
  });

  selector = new RowSelector<RadiusServer>({
    keyGetter: (server) => server.identifier,
    visibleRows: renderedRows(this.radiusDataSource)
  });

  onCreateNewServer(): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS_NEW);
  }

  onEditServer(server: RadiusServer): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS_DETAILS + server.identifier);
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
          title: $localize`:@@radiusServer.deleteRadiusServers:Delete RADIUS Servers`,
          items: selected.map((row) => row.identifier),
          itemType: "radius-server",
          confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          selected.forEach((row) => void this.radiusService.deleteRadiusServer(row.identifier).catch(() => undefined));
          this.selector.deselectAllRows();
        }
      });
  }

  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);

    const ds = this.radiusDataSource();
    ds.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.radiusDataSource();
    ds.filter = "";
    const inputEl = this.filterInput?.nativeElement as HTMLInputElement | undefined;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}
