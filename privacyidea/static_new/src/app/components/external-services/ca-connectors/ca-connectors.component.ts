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

import { Component, computed, ElementRef, inject, signal, ViewChild, WritableSignal } from "@angular/core";
import { toObservable, toSignal } from "@angular/core/rxjs-interop";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  CaConnector,
  CaConnectorService,
  CaConnectorServiceInterface
} from "@services/ca-connector/ca-connector.service";

import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { RowSelector } from "@services/table-utils/row-selector";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { finalize, switchMap } from "rxjs";

@Component({
  selector: "app-ca-connectors",
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
    CopyableComponent
  ],
  templateUrl: "./ca-connectors.component.html",
  styleUrl: "./ca-connectors.component.scss"
})
export class CaConnectorsComponent {
  protected readonly caConnectorService: CaConnectorServiceInterface = inject(CaConnectorService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  private readonly router = inject(Router);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength: WritableSignal<number> = computed(
    () => this.caConnectorService.caConnectors().length
  ) as WritableSignal<number>;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  displayedColumns: string[] = ["select", "connectorname", "type"];

  caConnectorDataSource = computed(() => {
    const connectors = this.caConnectorService.caConnectors();
    const dataSource = new MatTableDataSource(connectors);
    dataSource.paginator = this.paginator;
    dataSource.sort = this.sort;
    return dataSource;
  });

  private readonly renderedRows = toSignal(
    toObservable(this.caConnectorDataSource).pipe(
      switchMap((dataSource) => dataSource.connect().pipe(finalize(() => dataSource.disconnect())))
    ),
    { initialValue: [] as CaConnector[] }
  );

  selector = new RowSelector<CaConnector>({
    keyGetter: (connector) => connector.connectorname,
    visibleRows: this.renderedRows
  });

  openEditDialog(connector?: CaConnector): void {
    if (connector) {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_DETAILS + connector.connectorname);
    } else {
      this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_NEW);
    }
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
          title: $localize`Delete CA Connectors`,
          items: selected.map((row) => row.connectorname),
          itemType: "ca-connector",
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          selected.forEach(
            (row) => void this.caConnectorService.deleteCaConnector(row.connectorname).catch(() => undefined)
          );
          this.selector.deselectAllRows();
        }
      });
  }

  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);

    const ds = this.caConnectorDataSource();
    ds.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.caConnectorDataSource();
    ds.filter = "";
    const inputEl = this.filterInput?.nativeElement as HTMLInputElement | undefined;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}
