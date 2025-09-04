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
import { Component, ViewChild, WritableSignal, inject, linkedSignal } from "@angular/core";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource
} from "@angular/material/table";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { UserData, UserService, UserServiceInterface } from "../../../services/user/user.service";

import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { FormsModule } from "@angular/forms";
import { KeywordFilterComponent } from "../../shared/keyword-filter/keyword-filter.component";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { NgClass } from "@angular/common";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { MatSort, MatSortModule } from "@angular/material/sort";

const columnKeysMap = [
  { key: "username", label: "Username" },
  { key: "userid", label: "User ID" },
  { key: "givenname", label: "Given Name" },
  { key: "surname", label: "Surname" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "mobile", label: "Mobile" },
  { key: "description", label: "Description" },
  { key: "resolver", label: "Resolver" }
];

@Component({
  selector: "app-user-table",
  imports: [
    FormsModule,
    KeywordFilterComponent,
    MatCell,
    MatCellDef,
    MatFormField,
    MatLabel,
    MatInput,
    MatPaginator,
    MatTable,
    MatSortModule,
    MatHeaderCell,
    MatColumnDef,
    NgClass,
    MatHeaderRowDef,
    MatHeaderRow,
    MatRowDef,
    MatRow,
    MatNoDataRow,
    MatHeaderCellDef,
    ScrollToTopDirective,
    ClearableInputComponent
  ],
  templateUrl: "./user-table.component.html",
  styleUrl: "./user-table.component.scss"
})
export class UserTableComponent {
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  totalLength: WritableSignal<number> = linkedSignal({
    source: this.userService.usersResource.value,
    computation: (userResource, previous) => {
      if (userResource) {
        return userResource.result?.value?.length ?? 0;
      }
      return previous?.value ?? 0;
    }
  });
  emptyResource: WritableSignal<UserData[]> = linkedSignal({
    source: this.userService.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () =>
        Object.fromEntries(this.columnKeysMap.map((c) => [{ key: c.key, username: "" }]))
      )
  });
  usersDataSource: WritableSignal<MatTableDataSource<UserData>> = linkedSignal({
    source: this.userService.usersResource.value,
    computation: (userResource, previous) => {
      if (userResource) {
        const dataSource = new MatTableDataSource(userResource.result?.value);
        dataSource.paginator = this.paginator;
        dataSource.sort = this.sort;
        return dataSource;
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    }
  });
}
