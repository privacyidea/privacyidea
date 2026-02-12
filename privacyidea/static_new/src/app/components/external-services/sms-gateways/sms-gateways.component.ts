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

import { Component, computed, inject, signal, ViewChild, WritableSignal } from "@angular/core";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortModule } from "@angular/material/sort";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import {
  SmsGateway,
  SmsGatewayService,
  SmsGatewayServiceInterface
} from "../../../services/sms-gateway/sms-gateway.service";
import { NewSmsGatewayComponent } from "./new-sms-gateway/new-sms-gateway.component";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { MatTooltipModule } from "@angular/material/tooltip";
import { CommonModule } from "@angular/common";
import { DialogService, DialogServiceInterface } from "../../../services/dialog/dialog.service";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { SimpleConfirmationDialogComponent } from "../../shared/dialog/confirmation-dialog/confirmation-dialog.component";

@Component({
  selector: "app-sms-gateways",
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginator,
    MatSortModule,
    MatIconModule,
    MatButtonModule,
    MatDialogModule,
    MatTooltipModule,
    ScrollToTopDirective,
    MatFormField,
    MatLabel,
    ClearableInputComponent,
    MatInput,
    CopyButtonComponent
  ],
  templateUrl: "./sms-gateways.component.html",
  styleUrl: "./sms-gateways.component.scss"
})
export class SmsGatewaysComponent {
  protected readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  protected readonly dialog: MatDialog = inject(MatDialog);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  filterString = signal<string>("");
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  totalLength: WritableSignal<number> = computed(
    () => this.smsGatewayService.smsGateways().length
  ) as WritableSignal<number>;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: any;

  displayedColumns: string[] = ["name", "description", "providermodule", "actions"];

  smsDataSource = computed(() => {
    const gateways = this.smsGatewayService.smsGateways();
    const dataSource = new MatTableDataSource(gateways);
    dataSource.paginator = this.paginator;
    dataSource.sort = this.sort;
    return dataSource;
  });

  openEditDialog(gateway?: SmsGateway): void {
    this.dialog.open(NewSmsGatewayComponent, {
      data: gateway ? { ...gateway } : null,
      width: "800px"
    });
  }

  deleteGateway(gateway: SmsGateway): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Delete SMS Gateway`,
          items: [gateway.name],
          itemType: "sms-gateway",
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" },
          cancelAction: { label: $localize`Cancel`, value: false, type: "cancel" }
        }
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          this.smsGatewayService.deleteSmsGateway(gateway.name);
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
