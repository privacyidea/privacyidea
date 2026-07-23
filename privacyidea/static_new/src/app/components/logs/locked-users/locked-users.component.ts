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
import { DatePipe, NgClass } from "@angular/common";
import { Component, computed, inject, linkedSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatPaginatorModule, PageEvent } from "@angular/material/paginator";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltipModule } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { MultiSelectFilterComponent } from "@components/shared/multi-select-filter/multi-select-filter.component";
import { MultiSelectFilterOption } from "@components/shared/multi-select-filter/multi-select-filter-option";
import {
  ConditionalAccessStateService,
  ConditionalAccessStateServiceInterface,
  LockedUserEntry,
  LockedUsersPage
} from "@services/conditional-access-state/conditional-access-state.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "@services/resolver/resolver.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { from } from "rxjs";
import { concatMap, reduce } from "rxjs/operators";

@Component({
  selector: "app-locked-users",
  templateUrl: "./locked-users.component.html",
  styleUrl: "./locked-users.component.scss",
  imports: [
    ScrollToTopDirective,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatCheckboxModule,
    MatPaginatorModule,
    MatFormField,
    MatLabel,
    MatHint,
    MatInput,
    ClearableInputComponent,
    ScrollEdgesDirective,
    FilterValueButtonComponent,
    MultiSelectFilterComponent,
    RouterLink,
    NgClass,
    DatePipe
  ]
})
export class LockedUsersComponent {
  protected readonly casService: ConditionalAccessStateServiceInterface = inject(ConditionalAccessStateService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  readonly displayedColumns: string[] = [
    "select",
    "username",
    "realm",
    "resolver",
    "state",
    "lock_expires_at",
    "last_updated"
  ];

  // Alias for the template (sort icon + sort handler fallback).
  readonly sort = this.casService.lockedUsersSort;

  // Keep the previous total visible while a reload is in flight (mirrors the dataSource keep-previous).
  readonly totalLength = linkedSignal<PiResponse<LockedUsersPage> | undefined, number>({
    source: () =>
      this.casService.lockedUsersResource.hasValue() ? this.casService.lockedUsersResource.value() : undefined,
    computation: (resource, previous) => resource?.result?.value?.count ?? previous?.value ?? 0
  });

  readonly pageSizeOptions = computed(() => {
    const options = new Set(this.tableUtilsService.pageSizeOptions());
    options.add(this.casService.lockedUsersPageSize());
    return [...options].sort((a, b) => a - b);
  });

  // State filter options. Default selection (permanent + temporary) is seeded in the service's filter, so expired
  // records are hidden until "Expired" is picked.
  readonly stateOptions: MultiSelectFilterOption[] = [
    { label: $localize`Permanent`, value: "permanent" },
    { label: $localize`Temporary`, value: "temporary" },
    { label: $localize`Expired`, value: "expired" }
  ];

  // Keep the previously loaded rows visible while a reload is in flight
  readonly dataSource = linkedSignal<PiResponse<LockedUsersPage> | undefined, MatTableDataSource<LockedUserEntry>>({
    source: () =>
      this.casService.lockedUsersResource.hasValue() ? this.casService.lockedUsersResource.value() : undefined,
    computation: (resource, previous) => {
      if (resource) {
        return new MatTableDataSource(resource.result?.value?.locked_users ?? []);
      }
      return previous?.value ?? new MatTableDataSource<LockedUserEntry>([]);
    }
  });

  // Selection resets whenever the underlying data changes.
  readonly selection = linkedSignal<PiResponse<LockedUsersPage> | undefined, LockedUserEntry[]>({
    source: () =>
      this.casService.lockedUsersResource.hasValue() ? this.casService.lockedUsersResource.value() : undefined,
    computation: () => []
  });

  displayLogin(row: LockedUserEntry): string {
    return row.username || row.uid;
  }

  // A stale row (an expired timed lock still on record, shown only with "Show expired") is no longer enforced:
  // not permanent and with no time left.
  isExpired(row: LockedUserEntry): boolean {
    return !row.permanent && row.seconds_remaining === 0;
  }

  // Lock-expiry status badge (same colours as the user-details page): red = permanent, orange = actively
  // locked (timed, not yet elapsed), green = expired (stale record).
  lockStateClass(row: LockedUserEntry): string {
    if (row.permanent) {
      return "highlight-false";
    }
    return this.isExpired(row) ? "highlight-true" : "highlight-warning";
  }

  lockStateLabel(row: LockedUserEntry): string {
    if (row.permanent) {
      return $localize`Permanent`;
    }
    return this.isExpired(row) ? $localize`Expired` : $localize`Temporary`;
  }

  isAllSelected(): boolean {
    const rows = this.dataSource().data;
    return rows.length > 0 && this.selection().length === rows.length;
  }

  toggleAllRows(): void {
    this.selection.set(this.isAllSelected() ? [] : [...this.dataSource().data]);
  }

  toggleRow(row: LockedUserEntry): void {
    const current = this.selection();
    this.selection.set(current.includes(row) ? current.filter((r) => r !== row) : [...current, row]);
  }

  // --- filtering: CSV values per key, wildcard/case-insensitive server-side) ---

  // Free-text main filter input: edit the whole FilterValue string (e.g. "usernames: alice realm: myrealm").
  handleFilterInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.casService.lockedUsersFilter.set(this.casService.lockedUsersFilter().copyWith({ value }));
  }

  clearFilter(): void {
    this.casService.lockedUsersFilter.set(this.casService.lockedUsersFilter().copyWith({ value: "" }));
  }

  selectedFilterValues(keyword: string): string[] {
    return this.splitCsv(this.casService.lockedUsersFilter().getValueOfKey(keyword));
  }

  setFilterValues(keyword: string, values: string[]): void {
    const current = this.casService.lockedUsersFilter();
    const next = values.length ? current.addEntry(keyword, values.join(",")) : current.removeKey(keyword);
    this.casService.lockedUsersFilter.set(next);
  }

  addFilterValue(keyword: string, value: string): void {
    const current = this.selectedFilterValues(keyword);
    if (!current.includes(value)) {
      this.setFilterValues(keyword, [...current, value]);
    }
  }

  // Header keyword button (e.g. username): one click toggles a `keyword:` term in the main filter input for
  // the admin to type a value into.
  onKeywordClick(keyword: string): void {
    this.casService.lockedUsersFilter.set(
      this.tableUtilsService.toggleKeywordInFilter({
        keyword,
        currentValue: this.casService.lockedUsersFilter()
      })
    );
  }

  private splitCsv(value: string | undefined): string[] {
    return (value ?? "")
      .split(",")
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0);
  }

  // --- sorting ---

  onSortClick(columnKey: string): void {
    this.tableUtilsService.onSortButtonClick(columnKey, this.casService.lockedUsersSort, {
      active: "last_updated",
      direction: ""
    });
  }

  // --- pagination (mat-paginator is 0-based; the service/API page is 1-based) ---

  onPageEvent(event: PageEvent): void {
    this.casService.lockedUsersPageSize.set(event.pageSize);
    this.casService.lockedUsersPageIndex.set(event.pageIndex + 1);
  }

  resetSelected(): void {
    const rows = this.selection();
    if (rows.length === 0) {
      return;
    }
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Reset User Lockout`,
          items: rows.map((row) => this.displayLogin(row)),
          itemType: "locked user",
          confirmAction: { label: $localize`Reset`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        from(rows)
          .pipe(
            concatMap((row) =>
              this.casService.resetUserLockout({ uid: row.uid, realm: row.realm, resolver: row.resolver })
            ),
            reduce((count, success) => count + (success ? 1 : 0), 0)
          )
          .subscribe((count) => {
            if (count > 0) {
              this.notificationService.success($localize`Reset ${count} user lockout(s).`);
            }
            this.casService.lockedUsersResource.reload();
          });
      });
  }

  deleteExpired(): void {
    // Generic confirmation only: the set of expired records is evaluated server-side at purge time, so listing a
    // snapshot here could be misleading (more may expire in between). Admins can inspect them via the "Expired"
    // state filter beforehand.
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: $localize`Delete Expired Lockouts`,
          items: [],
          itemType: "expired lockout record",
          message: $localize`This permanently deletes all expired lockout records from the database.`,
          confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe((confirmed) => {
        if (!confirmed) {
          return;
        }
        this.casService.purgeUserLockouts().subscribe((count) => {
          this.notificationService.success($localize`Deleted ${count} expired lockout(s).`);
          this.casService.lockedUsersResource.reload();
        });
      });
  }
}
