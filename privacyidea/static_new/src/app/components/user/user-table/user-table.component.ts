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
  afterNextRender,
  Component,
  computed,
  ElementRef,
  inject,
  linkedSignal,
  OnDestroy,
  ViewChild,
  viewChild,
  WritableSignal
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
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { UserData, UserService, UserServiceInterface } from "@services/user/user.service";
import { inlineFilterHint } from "@utils/filter-hint.utils";

import { NgClass } from "@angular/common";
import { MatIconButton } from "@angular/material/button";
import { MatDialog } from "@angular/material/dialog";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { Sort } from "@angular/material/sort";
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterAutocompleteDirective } from "@components/shared/directives/filter-autocomplete.directive";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { UserNewResolverComponent } from "@components/user/user-new-resolver/user-new-resolver.component";
import { FilterOption } from "@core/models/filter_value_generic/filter-option";
import { FilterValueGeneric, keywordlessTerms } from "@core/models/filter_value_generic/filter-value-generic";
import { TableState } from "@core/models/table_state/table-state";
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

// Per-column predicates for the free-text search: a term matches if it is a substring of any column.
const userFilterOptions: FilterOption<UserData>[] = columnKeysMap.map(
  (column) =>
    new FilterOption<UserData>({
      key: column.key,
      label: column.label,
      matches: () => true,
      globalMatches: (item, term) =>
        String(item[column.key as keyof UserData] ?? "")
          .toLowerCase()
          .includes(term)
    })
);

@Component({
  selector: "app-user-table",
  imports: [
    FilterAutocompleteDirective,
    MatCell,
    MatCellDef,
    MatFormField,
    MatHint,
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
    ScrollEdgesDirective,
    TableStateComponent
  ],
  templateUrl: "./user-table.component.html",
  styleUrl: "./user-table.component.scss"
})
export class UserTableComponent implements OnDestroy {
  protected readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly resolverService = inject(ResolverService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly dialog = inject(MatDialog);
  readonly apiFilterKeys = this.userService.apiFilterKeys;
  readonly filterHint = inlineFilterHint();
  private basePageSizeOptions = [...this.tableUtilsService.pageSizeOptions()];
  readonly paginator = viewChild(MatPaginator);
  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;
  pageSizeOptions = computed(() => {
    if (!this.basePageSizeOptions.includes(this.userService.pageSize())) {
      this.basePageSizeOptions.push(this.userService.pageSize());
      this.basePageSizeOptions.sort((a, b) => a - b);
    }
    return this.basePageSizeOptions;
  });

  // Empty base; free-text terms are layered on per query to reuse the shared FilterValueGeneric model.
  private readonly freeTextFilter = new FilterValueGeneric<UserData>({ availableFilters: userFilterOptions });

  // Applied client-side across all columns of the fully-loaded user list, while keyword segments
  // (e.g. "username: root") go to the server via UserService.filterParams.
  readonly freeTextTerms = computed<string[]>(() =>
    keywordlessTerms(this.userService.activeFilter().filterString.toLowerCase())
  );

  // Free-text-filtered users, computed once and shared by both the row list and the total count so the
  // full list is not filtered twice per change.
  private readonly filteredUsers = computed<UserData[] | undefined>(() => {
    const userRes = this.userService.usersResource.hasValue() ? this.userService.usersResource.value() : undefined;
    if (!userRes) return undefined;
    return this.applyFreeText(userRes.result?.value ?? [], this.freeTextTerms());
  });

  totalLength: WritableSignal<number> = linkedSignal({
    source: () => this.filteredUsers(),
    computation: (filtered, previous) => (filtered ? filtered.length : (previous?.value ?? 0))
  });
  readonly skippedResolverNames = computed(() => this.userService.skippedResolvers().join(", "));

  readonly tableState = new TableState({
    resource: this.userService.usersResource,
    count: () => this.totalLength(),
    filterActive: () => !this.userService.activeFilter().isEmpty,
    allowed: () => this.authService.actionAllowed("userlist"),
    resetFilter: () => this.userService.clearFilter(),
    cancel: () => this.userService.usersResource.set(undefined)
  });
  usersDataSource: WritableSignal<MatTableDataSource<UserData>> = linkedSignal({
    source: () => ({
      filtered: this.filteredUsers(),
      sort: this.userService.sort(),
      paginator: this.paginator()
    }),
    computation: (src, prev) => {
      // While a reload is in flight the rows already on screen stay, rather than blanking the table.
      const data = src.filtered ?? prev?.value?.data ?? [];
      const sorted = this.clientsideSortUserData([...data], src.sort);
      const ds = new MatTableDataSource(sorted);
      ds.paginator = src.paginator ?? null;
      return ds;
    }
  });

  constructor() {
    // Autofocus the filter so the user can type immediately on entering the page.
    afterNextRender(() => this.filterInput?.nativeElement.focus());
  }

  ngOnDestroy(): void {
    // Do not carry a stale (and invisible) filter over to the next visit of the page.
    this.userService.clearFilter();
  }

  toggleFilter(filterKeyword: string): void {
    this.userService.updateFilter((current) =>
      this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: current
      })
    );
  }

  isFilterSelected(filter: string): boolean {
    return this.userService.activeFilter().hasKey(filter);
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

  // Keeps users where every term matches at least one column (AND across terms, OR across columns).
  private applyFreeText(data: UserData[], terms: string[]): UserData[] {
    if (!terms.length) return data;
    const filter = terms.reduce((acc, term) => acc.addFreeText(term), this.freeTextFilter);
    return filter.filterItems(data);
  }

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
}
