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
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSort, MatSortHeader, MatSortModule } from "@angular/material/sort";
import { MatCell, MatHeaderCell, MatHeaderRow, MatRow, MatTable, MatTableModule } from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { ContainerService, ContainerServiceInterface } from "../../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { OverflowService, OverflowServiceInterface } from "../../../../services/overflow/overflow.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../../services/table-utils/table-utils.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { CopyButtonComponent } from "../../../shared/copy-button/copy-button.component";
import { ContainerDetailsTokenTableComponent } from "./container-details-token-table.component";

@Component({
  selector: "app-container-details-token-table-self-service",
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatInput,
    MatLabel,
    MatPaginator,
    MatRow,
    MatSort,
    MatSortHeader,
    MatTable,
    NgClass,
    MatTableModule,
    MatSortModule,
    MatIcon,
    MatIconButton,
    MatButton,
    CopyButtonComponent,
    ReactiveFormsModule,
    FormsModule,
    MatTooltip
  ],
  templateUrl: "./container-details-token-table.self-service.component.html",
  styleUrl: "./container-details-token-table.component.scss"
})
export class ContainerDetailsTokenTableSelfServiceComponent extends ContainerDetailsTokenTableComponent {
  protected override readonly dialog: MatDialog = inject(MatDialog);
  protected override readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected override readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected override readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected override readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected override readonly contentService: ContentServiceInterface = inject(ContentService);
  protected override readonly authService: AuthServiceInterface = inject(AuthService);

  constructor() {
    super();
  }

  override isAssignableToAllToken = computed<boolean>(() => {
    const assignedUser = this.assignedUser();
    return assignedUser.user_name !== "";
  });
}
