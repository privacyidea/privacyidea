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
import { Component, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatPaginatorModule } from "@angular/material/paginator";
import { MatTableModule } from "@angular/material/table";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { ContainerTableComponent } from "@components/token/container-table/container-table.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "@services/container/container.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-container-table-self-service",
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    NgClass,
    CopyButtonComponent,
    MatCheckboxModule,
    FormsModule,
    MatIcon,
    MatButtonModule,
    ScrollToTopDirective
  ],
  templateUrl: "./container-table.self-service.component.html",
  styleUrl: "./container-table.component.scss"
})
export class ContainerTableSelfServiceComponent extends ContainerTableComponent {
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected override readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected override readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected override readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected override readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly router = inject(Router);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  navigateToCreate(): void {
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
  }

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
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Delete Container",
          items: [serial],
          itemType: "container",
          confirmAction: { label: "Delete", value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.deleteContainer(serial).subscribe({
              next: () => {
                this.notificationService.success($localize`Container deleted successfully.`);
                this.containerService.containerResource.reload();
              }
            });
          }
        }
      });
  }
}
