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
import { Component, inject } from "@angular/core";
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
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../services/token/token.service";
import { ConfirmationDialogComponent } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { ContainerTableComponent } from "./container-table.component";

@Component({
  selector: "app-container-table-self-service",
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
    MatIcon,
    MatIconButton,
    ScrollToTopDirective
  ],
  templateUrl: "./container-table.self-service.component.html",
  styleUrl: "./container-table.component.scss"
})
export class ContainerTableSelfServiceComponent extends ContainerTableComponent {
  private readonly dialog = inject(MatDialog);
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected override readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected override readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected override readonly contentService: ContentServiceInterface = inject(ContentService);

  readonly columnKeysMapSelfService = [
    { key: "serial", label: "Serial" },
    { key: "type", label: "Type" },
    { key: "states", label: "Status" },
    { key: "description", label: "Description" },
    { key: "delete", label: "Delete" }
  ];
  readonly columnKeysSelfService: string[] = this.columnKeysMapSelfService.map(
    (column: { key: string; label: string }) => column.key
  );

  constructor() {
    super();
  }

  deleteContainer(serial: string): void {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [serial],
          title: "Delete Container",
          type: "container",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.deleteContainer(serial).subscribe({
              next: () => {
                this.containerService.containerResource.reload();
              }
            });
          }
        }
      });
  }
}
