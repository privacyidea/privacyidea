/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  Component,
  computed,
  effect,
  inject,
  Input,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal,
  ElementRef
} from "@angular/core";
import {
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableDataSource,
  MatTableModule
} from "@angular/material/table";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { MatDialog } from "@angular/material/dialog";
import { MatPaginator, MatPaginatorModule } from "@angular/material/paginator";
import { NgClass } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatInput } from "@angular/material/input";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { Sort } from "@angular/material/sort";

@Component({
  selector: "app-container-details-token-table",
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatLabel,
    MatRow,
    MatTable,
    MatTableModule,
    MatIconButton,
    CopyButtonComponent,
    ReactiveFormsModule,
    FormsModule,
    MatPaginatorModule,
    NgClass,
    MatIconModule,
    MatTooltipModule,
    MatInput
  ],
  templateUrl: "./container-details-token-table.component.html",
  styleUrl: "./container-details-token-table.component.scss"
})
export class ContainerDetailsTokenTableComponent {
  protected readonly dialog: MatDialog = inject(MatDialog);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly columnsKeyMap = this.tableUtilsService.pickColumns("serial", "tokentype", "active", "username");
  readonly columnKeys = [...this.tableUtilsService.getColumnKeys(this.columnsKeyMap)];
  displayedColumns: string[] = [...this.columnsKeyMap.map((column) => column.key)];
  pageSize = 10;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  pageIndex = this.tokenService.pageIndex;
  @Input() containerTokenData!: WritableSignal<MatTableDataSource<ContainerDetailToken, MatPaginator>>;
  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
  filterValue: WritableSignal<string> = signal("");
  containerSerial = this.containerService.containerSerial;
  assignedUser: WritableSignal<{
    user_realm: string;
    user_name: string;
    user_resolver: string;
    user_id: string;
  }> = linkedSignal({
    source: () => this.containerService.containerDetail(),
    computation: (source) =>
      source.containers[0]?.users[0] ?? {
        user_realm: "",
        user_name: "",
        user_resolver: "",
        user_id: ""
      }
  });
  tokenSerial = this.tokenService.tokenSerial;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  apiFilter = this.tokenService.apiFilter;
  @ViewChild('filterInput', { static: false }) filterInput!: ElementRef<HTMLInputElement>;

  isAssignableToAllToken = computed<boolean>(() => {
    const assignedUser = this.assignedUser();
    if (assignedUser.user_name === "") {
      return false;
    }
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username === "");
  });

  isUnassignableFromAllToken = computed<boolean>(() => {
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username !== "");
  });

  constructor() {
    if (this.authService.actionAllowed("container_remove_token")) {
      this.displayedColumns.push("remove");
    }
    if (this.authService.actionAllowed("delete")) {
      this.displayedColumns.push("delete");
    }
    effect(() => {
      if (!this.containerTokenData) {
        return;
      }
      const base = this.containerTokenData().data ?? [];
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData(base, this.sort());
    });

    effect(() => {
      const s = this.sort();
      const base = this.dataSource.data ?? [];
      this.dataSource.data = this.tableUtilsService.clientsideSortTokenData([...base], s);
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;

    if (this.containerTokenData) {
      const externalDS = this.containerTokenData();
      externalDS.paginator = this.paginator;
      (externalDS as any)._sort = this.sort;
    }
    (this.dataSource as any)._sort = this.sort;

    this.dataSource.filterPredicate = (row: ContainerDetailToken, filter: string) => {
      const haystack = [
        row.serial,
        row.tokentype,
        row.username,
        String(row.active)
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(filter);
    };
  }

  handleFilterInput($event: Event): void {
    const raw = ($event.target as HTMLInputElement).value ?? "";
    const trimmed = raw.trim();
    this.filterValue.set(trimmed);
    const normalised = trimmed.toLowerCase();
    this.dataSource.filter = normalised;

    if (this.containerTokenData) {
      this.containerTokenData().filter = normalised;
    }
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [tokenSerial],
          title: "Remove Token",
          type: "token",
          action: "remove",
          numberOfTokens: [tokenSerial].length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result?.confirmed) {
            this.containerService.removeTokenFromContainer(containerSerial, tokenSerial).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              }
            });
          }
        }
      });
  }

  handleColumnClick(columnKey: string, token: ContainerDetailToken) {
    if (columnKey === "active") {
      this.toggleActive(token);
    }
  }

  toggleActive(token: ContainerDetailToken): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      }
    });
  }

  deleteAllTokens() {
    const serialList = this.containerTokenData().data.map((token) => token.serial);
    this.tokenService.bulkDeleteWithConfirmDialog(
      serialList,
      this.dialog,
      this.containerService.containerDetailResource.reload
    );
  }

  deleteTokenFromContainer(tokenSerial: string) {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [tokenSerial],
          title: "Delete Token",
          type: "token",
          action: "delete",
          numberOfTokens: [tokenSerial].length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result?.confirmed) {
            this.tokenService.deleteToken(tokenSerial).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              }
            });
          }
        }
      });
  }
}
