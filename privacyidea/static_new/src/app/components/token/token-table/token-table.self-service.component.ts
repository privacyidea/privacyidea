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
import { NgClass } from "@angular/common";
import { Component, computed, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatIconButton } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatDialog } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatSortModule } from "@angular/material/sort";
import { MatTableModule } from "@angular/material/table";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ConfirmationDialogComponent } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { ScrollAdjusterDirective } from "../../shared/directives/scroll-adjuster.directive";
import { TokenTableComponent } from "./token-table.component";

@Component({
  selector: "app-token-table-self-service",
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    CopyButtonComponent,
    MatCheckboxModule,
    FormsModule,
    MatIconButton,
    MatIcon,
    ScrollAdjusterDirective
  ],
  templateUrl: "./token-table.self-service.component.html",
  styleUrl: "./token-table.component.scss"
})
export class TokenTableSelfServiceComponent extends TokenTableComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private dialog = inject(MatDialog);
  columnKeysMapSelfService = computed(() => {
    const columnKeys = [
      { key: "serial", label: "Serial" },
      { key: "tokentype", label: "Type" },
      { key: "description", label: "Description" },
      { key: "container_serial", label: "Container" },
      { key: "active", label: "Active" },
      { key: "failcount", label: "Fail Counter" }
    ];
    if (this.authService.actionAllowed("revoke")) columnKeys.push({ key: "revoke", label: "Revoke" });
    if (this.authService.actionAllowed("delete")) columnKeys.push({ key: "delete", label: "Delete" });

    return columnKeys;
  });
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService().map(
    (column: { key: string; label: string }) => column.key
  );

  revokeToken(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [serial],
          title: "Revoke Token",
          type: "token",
          action: "revoke",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          this.tokenService.revokeToken(serial).subscribe({
            next: () => {
              if (result) {
                this.tokenService.tokenResource.reload();
              }
            }
          });
        }
      });
  }

  deleteToken(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [serial],
          title: "Delete Token",
          type: "token",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          this.tokenService.deleteToken(serial).subscribe({
            next: () => {
              if (result) {
                this.tokenService.tokenResource.reload();
              }
            }
          });
        }
      });
  }
}
