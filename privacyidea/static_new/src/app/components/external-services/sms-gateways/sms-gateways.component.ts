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
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { SmsGateway, SmsGatewayService, SmsGatewayServiceInterface } from "@services/sms-gateway/sms-gateway.service";

import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { RowSelector } from "@services/table-utils/row-selector";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { finalize, switchMap } from "rxjs";

@Component({
  selector: "app-sms-gateways",
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
  templateUrl: "./sms-gateways.component.html",
  styleUrl: "./sms-gateways.component.scss"
})
export class SmsGatewaysComponent {
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private readonly router = inject(Router);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength: WritableSignal<number> = computed(
    () => this.smsGatewayService.smsGateways().length
  ) as WritableSignal<number>;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  displayedColumns: string[] = ["select", "name", "description", "providermodule"];

  smsDataSource = computed(() => {
    const gateways = this.smsGatewayService.smsGateways();
    const dataSource = new MatTableDataSource(gateways);
    dataSource.paginator = this.paginator;
    dataSource.sort = this.sort;
    return dataSource;
  });

  private readonly renderedRows = toSignal(
    toObservable(this.smsDataSource).pipe(
      switchMap((dataSource) => dataSource.connect().pipe(finalize(() => dataSource.disconnect())))
    ),
    { initialValue: [] as SmsGateway[] }
  );

  selector = new RowSelector<SmsGateway>({ keyGetter: (gateway) => gateway.name, visibleRows: this.renderedRows });

  onCreateNewGateway(): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS_NEW);
  }

  onEditGateway(gateway: SmsGateway): void {
    this.router.navigateByUrl(ROUTE_PATHS.EXTERNAL_SERVICES_SMS_DETAILS + gateway.name);
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
          title: $localize`Delete SMS Gateways`,
          items: selected.map((gateway) => gateway.name),
          itemType: "sms-gateway",
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          selected.forEach(
            (gateway) => void this.smsGatewayService.deleteSmsGateway(gateway.name).catch(() => undefined)
          );
          this.selector.deselectAllRows();
        }
      });
  }

  onFilterInput(value: string): void {
    const trimmed = (value ?? "").trim();
    this.filterString.set(trimmed);

    const ds = this.smsDataSource();
    ds.filter = trimmed.toLowerCase();
  }

  resetFilter(): void {
    this.filterString.set("");
    const ds = this.smsDataSource();
    ds.filter = "";
    const inputEl = this.filterInput?.nativeElement as HTMLInputElement | undefined;
    if (inputEl) {
      inputEl.value = "";
    }
  }
}
