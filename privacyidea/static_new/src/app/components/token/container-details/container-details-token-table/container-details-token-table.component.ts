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
import { Component, Input, ViewChild, WritableSignal, computed, effect, inject, linkedSignal } from "@angular/core";
import {
  ContainerDetailToken,
  ContainerService,
  ContainerServiceInterface
} from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
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
import { MatSort, MatSortHeader, MatSortModule } from "@angular/material/sort";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { MatDialog } from "@angular/material/dialog";
import { MatPaginator, MatPaginatorModule } from "@angular/material/paginator";
import { NgClass } from "@angular/common";
import { f } from "../../../../../../node_modules/@angular/material/icon-module.d-d06a5620";
import { MatIconModule } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatInput } from "@angular/material/input";

const columnsKeyMap = [
  { key: "serial", label: "Serial" },
  { key: "tokentype", label: "Type" },
  { key: "active", label: "Active" },
  { key: "username", label: "User" }
];

@Component({
  selector: "app-container-details-token-table",
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatLabel,
    MatRow,
    MatSort,
    MatSortHeader,
    MatTable,
    MatTableModule,
    MatSortModule,
    MatIconButton,
    MatButton,
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

  protected readonly columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = [...columnsKeyMap.map((column) => column.key)];
  pageSize = 10;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  filterValue = "";
  @Input() containerTokenData!: WritableSignal<MatTableDataSource<ContainerDetailToken, MatPaginator>>;
  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
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
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

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
      this.dataSource.data = this.containerTokenData().data ?? [];
    });
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;

    if (this.containerTokenData) {
      const externalDS = this.containerTokenData();
      externalDS.paginator = this.paginator;
      externalDS.sort = this.sort;
    }
  }

  handleFilterInput($event: Event): void {
    this.filterValue = ($event.target as HTMLInputElement).value.trim();
    const normalised = this.filterValue.toLowerCase();
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
          if (result) {
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

  unassignFromAllToken() {
    const tokenToUnassign = this.containerTokenData().data.filter((token) => token.username !== "");
    if (tokenToUnassign.length === 0) {
      return;
    }
    const tokenSerials = tokenToUnassign.map((token) => token.serial);
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          type: "token",
          serialList: tokenSerials,
          title: "Unassign User from All Tokens",
          action: "unassign",
          numberOfTokens: tokenSerials.length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.unassignUserFromAll(tokenSerials).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              },
              error: (error) => {
                console.error("Error unassigning user from token:", error);
              }
            });
          }
        }
      });
  }

  assignToAllToken() {
    const username = this.assignedUser().user_name;
    const realm = this.assignedUser().user_realm;
    const tokensToAssign = this.containerTokenData().data.filter((token) => {
      return token.username !== username;
    });
    if (tokensToAssign.length === 0) {
      return;
    }
    const tokensAssignedToOtherUser = tokensToAssign.filter((token) => token.username !== "");
    const tokenSerialsAssignedToOtherUser = tokensAssignedToOtherUser.map((token) => token.serial);
    this.tokenService.unassignUserFromAll(tokenSerialsAssignedToOtherUser).subscribe({
      next: () => {
        const tokenSerialsToAssign = tokensToAssign.map((token) => token.serial);
        this.tokenService
          .assignUserToAll({
            tokenSerials: tokenSerialsToAssign,
            username: username,
            realm: realm
          })
          .subscribe({
            next: () => this.containerService.containerDetailResource.reload(),
            error: (error) => console.error("Error assigning user to all tokens:", error)
          });
      }
    });
  }

  toggleActive(token: ContainerDetailToken): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      }
    });
  }

  toggleAll(action: "activate" | "deactivate") {
    this.containerService.toggleAll(action).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      }
    });
  }

  removeAll() {
    const serialList = this.containerTokenData()
      .data.map((token) => token.serial)
      .join(",");
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: serialList.split(","),
          title: "Remove Token",
          type: "token",
          action: "remove",
          numberOfTokens: serialList.split(",").length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.removeAll(this.containerSerial()).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              }
            });
          }
        }
      });
  }

  deleteAllTokens() {
    const serialList = this.containerTokenData()
      .data.map((token) => token.serial)
      .join(",");
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: serialList.split(","),
          title: "Delete All Tokens",
          type: "token",
          action: "delete",
          numberOfTokens: serialList.split(",").length
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService
              .deleteAllTokens({
                containerSerial: this.containerSerial(),
                serialList: serialList
              })
              .subscribe({
                next: () => {
                  this.containerService.containerDetailResource.reload();
                }
              });
          }
        }
      });
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
          if (result) {
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
