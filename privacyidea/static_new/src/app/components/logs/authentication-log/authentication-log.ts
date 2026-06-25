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
import { Component, computed, ElementRef, inject, linkedSignal, ViewChild, WritableSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
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
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { MultiSelectFilterComponent } from "@components/shared/multi-select-filter/multi-select-filter.component";
import {
  AuthenticationLogEntry,
  AuthenticationLogService,
  AuthenticationLogServiceInterface
} from "@services/authentication-log/authentication-log.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

type EventSeverity = "success" | "failure" | "neutral";

// CSS highlight class per event severity (defined in styles/table.scss).
const SEVERITY_CLASS: Record<EventSeverity, string> = {
  success: "highlight-true",
  failure: "highlight-false",
  neutral: "highlight-warning"
};

// All authentication-log event types with their outcome severity, mirroring AuthEventType in
// privacyidea/lib/conditional_access/authentication_event_types.py. Severity drives both the predefined filter
// options and the row coloring, so add new backend event types here (a missing one is simply not offered/colored).
const AUTH_EVENT_TYPES: readonly { value: string; severity: EventSeverity }[] = [
  { value: "LOGIN_SUCCESS", severity: "success" },
  { value: "CHALLENGE_TRIGGERED", severity: "neutral" },
  { value: "CHALLENGE_CONTINUED", severity: "neutral" },
  { value: "CHALLENGE_ANSWERED_OUT_OF_BAND", severity: "neutral" },
  { value: "CHALLENGE_ANSWERED_FAIL", severity: "failure" },
  { value: "CHALLENGE_DECLINED", severity: "failure" },
  { value: "ENROLLMENT_TRIGGERED", severity: "neutral" },
  { value: "ENROLLMENT_CANCELED_FAIL", severity: "failure" },
  { value: "NOT_AUTHORIZED", severity: "failure" },
  { value: "PASSWORD_FAIL", severity: "failure" },
  { value: "PIN_FAIL", severity: "failure" },
  { value: "TOKEN_ONLY_FAIL", severity: "failure" },
  { value: "MFA_FAIL", severity: "failure" },
  { value: "USER_UNKNOWN", severity: "failure" },
  { value: "NO_TOKEN", severity: "failure" },
  { value: "NO_USABLE_TOKEN", severity: "failure" },
  { value: "UNKNOWN_FAIL_REASON", severity: "failure" }
];

const SEVERITY_BY_EVENT_TYPE: Record<string, EventSeverity> = Object.fromEntries(
  AUTH_EVENT_TYPES.map((entry) => [entry.value, entry.severity])
);

// `sortable` mirrors SORTABLE_COLUMNS in privacyidea/lib/conditional_access/authentication_log.py. Every column is
// sortable except `other_info`, which is a JSON column the backend cannot order on meaningfully.
const columnKeysMap: { key: string; label: string; filterable: boolean; sortable: boolean }[] = [
  { key: "timestamp", label: "Timestamp", filterable: false, sortable: true },
  { key: "event_type", label: "Event Type", filterable: true, sortable: true },
  { key: "username", label: "User", filterable: true, sortable: true },
  { key: "realm", label: "Realm", filterable: true, sortable: true },
  { key: "resolver", label: "Resolver", filterable: true, sortable: true },
  { key: "uid", label: "UID", filterable: true, sortable: true },
  { key: "source_ip", label: "Source IP", filterable: true, sortable: true },
  { key: "client_label", label: "Client", filterable: true, sortable: true },
  { key: "serial", label: "Serial", filterable: true, sortable: true },
  { key: "transaction_id", label: "Transaction ID", filterable: true, sortable: true },
  { key: "previous_transaction_id", label: "Previous Transaction ID", filterable: true, sortable: true },
  { key: "other_info", label: "Info", filterable: false, sortable: false }
];

@Component({
  selector: "app-authentication-log",
  imports: [
    MatCell,
    MatFormField,
    MatInput,
    MatPaginator,
    MatHeaderCellDef,
    MatHeaderCell,
    MatTable,
    MatCellDef,
    NgClass,
    MatHeaderRowDef,
    MatHeaderRow,
    MatRowDef,
    MatNoDataRow,
    MatRow,
    MatColumnDef,
    MatLabel,
    CopyableComponent,
    RouterLink,
    ScrollToTopDirective,
    ClearableInputComponent,
    MultiSelectFilterComponent,
    MatIcon,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule
  ],
  templateUrl: "./authentication-log.html",
  styleUrl: "./authentication-log.scss"
})
export class AuthenticationLog {
  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);
  readonly eventTypeOptions: readonly string[] = AUTH_EVENT_TYPES.map((entry) => entry.value);
  protected readonly authenticationLogService: AuthenticationLogServiceInterface = inject(AuthenticationLogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  sort = this.authenticationLogService.sort;

  @ViewChild("filterHTMLInputElement", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;

  totalLength: WritableSignal<number> = linkedSignal({
    source: () =>
      this.authenticationLogService.authenticationLogResource.hasValue()
        ? this.authenticationLogService.authenticationLogResource.value()
        : undefined,
    computation: (resource, previous) => resource?.result?.value?.count ?? previous?.value ?? 0
  });
  emptyResource: WritableSignal<AuthenticationLogEntry[]> = linkedSignal({
    source: this.authenticationLogService.pageSize,
    computation: (pageSize: number) =>
      Array.from(
        { length: pageSize },
        () => Object.fromEntries(this.columnKeysMap.map((col) => [col.key, ""])) as unknown as AuthenticationLogEntry
      )
  });
  dataSource: WritableSignal<MatTableDataSource<AuthenticationLogEntry>> = linkedSignal({
    source: () =>
      this.authenticationLogService.authenticationLogResource.hasValue()
        ? this.authenticationLogService.authenticationLogResource.value()
        : undefined,
    computation: (resource, previous) => {
      if (resource) {
        return new MatTableDataSource(resource.result?.value?.auth_logs);
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    }
  });
  private readonly basePageSizeOptions = this.tableUtilsService.pageSizeOptions();
  // Pure derivation: the base options plus the active page size (if custom), deduped and sorted.
  pageSizeOptions = computed(() =>
    [...new Set([...this.basePageSizeOptions, this.authenticationLogService.pageSize()])].sort((a, b) => a - b)
  );
  noDataText = computed(() =>
    this.authenticationLogService.filterParams()
      ? $localize`No authentication log entries matching the filter.`
      : $localize`No authentication log entries.`
  );

  onPageEvent(event: PageEvent): void {
    this.authenticationLogService.pageSize.set(event.pageSize);
    // mat-paginator emits a 0-based index; the service/API page is 1-based.
    this.authenticationLogService.pageIndex.set(event.pageIndex + 1);
  }

  onKeywordClick(filterKeyword: string): void {
    this.authenticationLogService.authenticationLogFilter.set(
      this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: this.authenticationLogService.authenticationLogFilter()
      })
    );
    this.filterInput?.nativeElement.focus();
  }

  getFilterIconName(keyword: string): string {
    return this.authenticationLogService.authenticationLogFilter().hasKey(keyword) ? "filter_alt_off" : "filter_alt";
  }

  // Three-state sort cycle per column: ascending -> descending -> cleared. Clearing falls back to the default order
  // (timestamp desc); the empty direction makes every column show the neutral sort icon.
  onSortClick(columnKey: string): void {
    const current = this.sort();
    if (current.active !== columnKey || !current.direction) {
      this.sort.set({ active: columnKey, direction: "asc" });
    } else if (current.direction === "asc") {
      this.sort.set({ active: columnKey, direction: "desc" });
    } else {
      this.sort.set({ active: "timestamp", direction: "" });
    }
  }

  // Predefined-value filters (event_type, realm) hold one or more comma-separated values the API splits as CSV.
  // The shared multi-select-filter component renders these and emits the full next selection.
  selectedFilterValues(keyword: string): string[] {
    return this.splitCsv(this.authenticationLogService.authenticationLogFilter().getValueOfKey(keyword));
  }

  setFilterValues(keyword: string, values: string[]): void {
    const currentFilter = this.authenticationLogService.authenticationLogFilter();
    const newFilter = values.length
      ? currentFilter.addEntry(keyword, values.join(","))
      : currentFilter.removeKey(keyword);
    this.authenticationLogService.authenticationLogFilter.set(newFilter);
  }

  // Color a row by its event's outcome severity (success/failure/neutral); unknown/empty values stay unstyled.
  getEventTypeClass(value: string): string {
    const severity = SEVERITY_BY_EVENT_TYPE[value];
    return severity ? SEVERITY_CLASS[severity] : "";
  }

  formatInfo(value: AuthenticationLogEntry["other_info"]): string {
    return value ? JSON.stringify(value) : "";
  }

  // The serial column may hold several comma-separated serials; render each as its own token link.
  splitSerials(value: string | null | undefined): string[] {
    return this.splitCsv(value);
  }

  private splitCsv(value: string | null | undefined): string[] {
    return value
      ? value
          .split(",")
          .map((entry) => entry.trim())
          .filter((entry) => entry.length > 0)
      : [];
  }
}
