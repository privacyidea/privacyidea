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
import { Component, ElementRef, ViewChild, WritableSignal, inject, linkedSignal, signal } from "@angular/core";
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
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { NgClass } from "@angular/common";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { Sort } from "@angular/material/sort";
import { RouterLink } from "@angular/router";
import { UserTableActionsComponent } from "./user-table-actions/user-table-actions.component";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";

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
    MatCell,
    MatCellDef,
    MatFormField,
    MatLabel,
    MatInput,
    MatPaginator,
    MatTable,
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
    ClearableInputComponent,
    UserTableActionsComponent,
    ClearableInputComponent,
    RouterLink,
    MatIcon,
    MatIconButton
  ],
  templateUrl: "./user-table.component.html",
  styleUrl: "./user-table.component.scss"
})
export class UserTableComponent {
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild('filterHTMLInputElement', { static: false }) filterInput!: ElementRef<HTMLInputElement>;
  sort = signal({ active: 'username', direction: 'asc' } as Sort);
  readonly apiFilter = this.userService.apiFilterOptions;
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
    source: () => ({
      userRes: this.userService.usersResource.value(),
      sort: this.sort()
    }),
    computation: (src, prev) => {
      const data = src.userRes?.result?.value ?? prev?.value?.data ?? this.emptyResource();
      const sorted = this.sortData([...data], this.sort());
      const ds = new MatTableDataSource(sorted);
      ds.paginator = this.paginator;
      return ds;
    }
  });

  private sortData(data: UserData[], s: Sort): UserData[] {
    if (!s.direction) return data;
    const dir = s.direction === 'asc' ? 1 : -1;
    const key = s.active as keyof UserData;
    return data.sort((a: any, b: any) => {
      const va = (a?.[key] ?? '').toString().toLowerCase();
      const vb = (b?.[key] ?? '').toString().toLowerCase();
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
  }

  toggleFilter(filterKeyword: string): void {
    const newValue = this.tableUtilsService.toggleKeywordInFilter({
      keyword: filterKeyword,
      currentValue: this.userService.apiUserFilter()
    });
    this.userService.apiUserFilter.set(newValue);
  }

  isFilterSelected(filter: string): boolean {
    return this.userService.apiUserFilter().hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    return this.isFilterSelected(keyword) ? 'filter_alt_off' : 'filter_alt';
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  onClickUsername(user: UserData): void {
    this.userService.detailsUsername.set(user.username);
  }
}
