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
import { NgClass } from "@angular/common";
import { Component, computed, inject } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatDialog } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatTableModule } from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { TokenTableComponent } from "./token-table.component";

@Component({
  selector: "app-token-table-self-service",
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    NgClass,
    CopyableComponent,
    MatCheckboxModule,
    MatButton,
    MatIconButton,
    MatIcon,
    MatTooltip,
    ScrollToTopDirective,
    StickyHeaderDirective,
    ScrollEdgesDirective,
    TableStateComponent,
    RouterLink
  ],
  templateUrl: "./token-table.self-service.component.html",
  styleUrl: "./token-table.component.scss"
})
export class TokenTableSelfServiceComponent extends TokenTableComponent {
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private dialog = inject(MatDialog);
  override readonly tableState = new TableState({
    resource: this.tokenResource,
    count: () => this.totalLength(),
    filterActive: () => !this.activeFilter().isEmpty,
    resetFilter: () => this.tokenService.clearFilter()
  });
  columnKeysMapSelfService = computed(() => {
    const columnKeys = [
      { key: "serial", label: $localize`:@@common.serial:Serial` },
      { key: "tokentype", label: $localize`:@@common.type:Type` },
      { key: "description", label: $localize`:@@common.description:Description` },
      { key: "container_serial", label: $localize`:@@common.container:Container` },
      { key: "active", label: $localize`:@@common.active:Active` },
      { key: "failcount", label: $localize`:@@token.failCounter:Fail Counter` }
    ];
    if (this.authService.actionAllowed("revoke"))
      columnKeys.push({ key: "revoke", label: $localize`:@@token.revoke:Revoke` });
    if (this.authService.actionAllowed("delete"))
      columnKeys.push({ key: "delete", label: $localize`:@@common.delete:Delete` });

    return columnKeys;
  });
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService().map(
    (column: { key: string; label: string }) => column.key
  );

  revokeToken(serial: string): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@token.revokeToken:Revoke Token`,
          items: [serial],
          itemType: $localize`:@@common.itemTypeToken:token`,
          confirmAction: { label: $localize`:@@token.revoke:Revoke`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.revokeToken(serial).subscribe({
              next: () => this.tokenService.tokenResource.reload()
            });
          }
        }
      });
  }

  deleteToken(serial: string): void {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`:@@common.deleteToken:Delete Token`,
          items: [serial],
          itemType: $localize`:@@common.itemTypeToken:token`,
          confirmAction: { label: $localize`:@@common.delete:Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.deleteToken(serial).subscribe({
              next: () => this.tokenService.tokenResource.reload()
            });
          }
        }
      });
  }
}
