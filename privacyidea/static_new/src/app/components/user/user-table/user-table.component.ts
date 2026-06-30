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
import {
  Component,
  ElementRef,
  ViewChild,
  WritableSignal,
  computed,
  inject,
  linkedSignal,
  signal
} from "@angular/core";
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
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { UserData, UserService, UserServiceInterface } from "@services/user/user.service";

import { NgClass } from "@angular/common";
import { MatIconButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import { MatTooltipModule } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { UserNewResolverComponent } from "@components/user/user-new-resolver/user-new-resolver.component";
import { ResolverService } from "@services/resolver/resolver.service";
import { UserTableActionsComponent } from "./user-table-actions/user-table-actions.component";

const columnKeysMap = [
  { key: "username", label: $localize`Username` },
  { key: "userid", label: $localize`User ID` },
  { key: "givenname", label: $localize`Given Name` },
  { key: "surname", label: $localize`Surname` },
  { key: "email", label: $localize`Email` },
  { key: "phone", label: $localize`Phone` },
  { key: "mobile", label: $localize`Mobile` },
  { key: "description", label: $localize`Description` },
  { key: "resolver", label: $localize`Resolver` }
];

@Component({
  selector: "app-user-table",
  imports: [
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
    CopyableComponent,
    UserTableActionsComponent,
    RouterLink,
    MatIcon,
    MatIconButton,
    MatTooltipModule
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
  protected readonly resolverService = inject(ResolverService);
  protected readonly dialog = inject(MatDialog);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;
  sort = signal({ active: "", direction: "" } as Sort);
  readonly apiFilter = this.userService.apiFilterOptions;

  private basePageSizeOptions = [...this.tableUtilsService.pageSizeOptions()];
  pageSizeOptions = computed(() => {
    if (!this.basePageSizeOptions.includes(this.userService.pageSize())) {
      this.basePageSizeOptions.push(this.userService.pageSize());
      this.basePageSizeOptions.sort((a, b) => a - b);
    }
    return this.basePageSizeOptions;
  });

  totalLength: WritableSignal<number> = linkedSignal({
    source: () => (this.userService.usersResource.hasValue() ? this.userService.usersResource.value() : undefined),
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
      userRes: this.userService.usersResource.hasValue() ? this.userService.usersResource.value() : undefined,
      sort: this.sort()
    }),
    computation: (src, prev) => {
      const data = src.userRes?.result?.value ?? prev?.value?.data ?? this.emptyResource();
      const sorted = this.clientsideSortUserData([...data], this.sort());
      const ds = new MatTableDataSource(sorted);
      ds.paginator = this.paginator;
      return ds;
    }
  });

  private clientsideSortUserData(data: UserData[], s: Sort): UserData[] {
    if (!s.direction) return data;
    const dir = s.direction === "asc" ? 1 : -1;
    const key = s.active as keyof UserData;
    return data.sort((a: UserData, b: UserData) => {
      const va = (a?.[key] ?? "").toString().toLowerCase();
      const vb = (b?.[key] ?? "").toString().toLowerCase();
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
    return this.isFilterSelected(keyword) ? "filter_alt_off" : "filter_alt";
  }

  onFilterClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  onClickUsername(user: UserData): void {
    this.userService.detailsUser.set({ username: user.username, realm: this.userService.selectedUserRealm() });
  }

  onClickResolver(resolverName: string): void {
    const resolver = this.resolverService.resolvers().find((r) => r.resolvername === resolverName);
    if (resolver) {
      this.dialog.open(UserNewResolverComponent, {
        data: { resolver },
        width: "auto",
        height: "auto",
        maxWidth: "100vw",
        maxHeight: "100vh"
      });
    }
  }
}
