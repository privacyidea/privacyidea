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
import { Component, computed, ElementRef, inject, linkedSignal, ViewChild, WritableSignal } from "@angular/core";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
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
import { AuditData, AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

import { NgClass } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { FilterAutocompleteDirective } from "@components/shared/directives/filter-autocomplete.directive";
import { filterInputHint } from "@utils/filter-hint.utils";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { LocalDateTimePipe } from "@components/shared/pipes/local-date-time.pipe";
import { FilterValue } from "@core/models/filter_value/filter_value";

type AuditCellRenderType =
  | "status-span"
  | "highlight-ok"
  | "date"
  | "policies-csv"
  | "copy-text"
  | "serial-link"
  | "container-link"
  | "user-link"
  | "default";

const cellRenderTypeByKey: Record<string, AuditCellRenderType> = {
  success: "status-span",
  authentication: "status-span",
  sig_check: "highlight-ok",
  missing_line: "highlight-ok",
  startdate: "date",
  date: "date",
  policies: "policies-csv",
  serial: "serial-link",
  container_serial: "container-link",
  user: "user-link",
  action: "copy-text",
  action_detail: "copy-text",
  info: "copy-text",
  user_agent: "copy-text",
  privacyidea_server: "copy-text",
  realm: "copy-text",
  administrator: "copy-text",
  client: "copy-text",
  resolver: "copy-text"
};

const columnKeysMap = [
  { key: "number", label: $localize`Number` },
  { key: "action", label: $localize`Action` },
  { key: "success", label: $localize`Success` },
  { key: "authentication", label: $localize`Authentication` },
  { key: "serial", label: $localize`Serial` },
  { key: "container_serial", label: $localize`Container Serial` },
  { key: "startdate", label: $localize`Start Date` },
  { key: "duration", label: $localize`Duration` },
  { key: "token_type", label: $localize`Token Type` },
  { key: "user", label: $localize`User` },
  { key: "realm", label: $localize`Realm` },
  { key: "administrator", label: $localize`Administrator` },
  { key: "action_detail", label: $localize`Action Detail` },
  { key: "info", label: $localize`Info` },
  { key: "policies", label: $localize`Policies` },
  { key: "client", label: $localize`Client` },
  { key: "user_agent", label: $localize`User Agent` },
  { key: "user_agent_version", label: $localize`User Agent Version` },
  { key: "privacyidea_server", label: $localize`PrivacyIDEA Server` },
  { key: "log_level", label: $localize`Log Level` },
  { key: "clearance_level", label: $localize`Clearance Level` },
  { key: "sig_check", label: $localize`Signature Check` },
  { key: "missing_line", label: $localize`Missing Line` },
  { key: "resolver", label: $localize`Resolver` },
  { key: "thread_id", label: $localize`Thread ID` },
  { key: "container_type", label: $localize`Container Type` }
];

@Component({
  selector: "app-audit",
  imports: [
    FilterAutocompleteDirective,
    MatCardModule,
    MatCell,
    MatFormField,
    MatHint,
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
    MatIcon,
    MatButtonModule,
    MatIconModule,
    ScrollEdgesDirective,
    LocalDateTimePipe
  ],
  templateUrl: "./audit.component.html",
  styleUrl: "./audit.component.scss"
})
export class AuditComponent {
  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);
  protected readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  readonly apiFilterKeyMap = this.auditService.apiFilterKeyMap;
  readonly filterHint = filterInputHint({ includeCaseNote: false, separator: " " });
  sort = this.auditService.sort;

  @ViewChild("filterHTMLInputElement", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;

  totalLength: WritableSignal<number> = linkedSignal({
    source: () => (this.auditService.auditResource.hasValue() ? this.auditService.auditResource.value() : undefined),
    computation: (auditResource, previous) => {
      return auditResource?.result?.value?.count ?? previous?.value ?? 0;
    }
  });
  emptyResource: WritableSignal<AuditData[]> = linkedSignal({
    source: this.auditService.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => Object.fromEntries(this.columnKeysMap.map((col) => [col.key, ""])))
  });
  auditDataSource: WritableSignal<MatTableDataSource<AuditData>> = linkedSignal({
    source: () => (this.auditService.auditResource.hasValue() ? this.auditService.auditResource.value() : undefined),
    computation: (auditResource, previous) => {
      if (auditResource) {
        return new MatTableDataSource(auditResource.result?.value?.auditdata);
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    }
  });
  basePageSizeOptions = [...this.tableUtilsService.pageSizeOptions()];
  pageSizeOptions = computed(() => {
    if (!this.basePageSizeOptions.includes(this.auditService.pageSize())) {
      this.basePageSizeOptions.push(this.auditService.pageSize());
      this.basePageSizeOptions.sort((a, b) => a - b);
    }
    return this.basePageSizeOptions;
  });

  onPageEvent(event: PageEvent) {
    this.auditService.pageSize.set(event.pageSize);
    this.auditService.pageIndex.set(event.pageIndex);
  }

  toggleFilter(filterKeyword: string): void {
    let newValue;
    if (filterKeyword === "success") {
      newValue = this.tableUtilsService.toggleBooleanInFilter({
        keyword: filterKeyword,
        currentValue: this.auditService.auditFilter()
      });
    } else {
      newValue = this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: this.auditService.auditFilter()
      });
    }
    this.auditService.auditFilter.set(newValue);
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "success") {
      const value = this.auditService.auditFilter()?.getValueOfKey(keyword)?.toLowerCase();
      if (!value) {
        return "filter_alt";
      }
      return value === "true" ? "screen_rotation_alt" : value === "false" ? "filter_alt_off" : "filter_alt";
    } else {
      const isSelected = this.auditService.auditFilter().hasKey(keyword);
      return isSelected ? "filter_alt_off" : "filter_alt";
    }
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  getCellRenderType(columnKey: string): AuditCellRenderType {
    return cellRenderTypeByKey[columnKey] ?? "default";
  }
}
