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
import { AuditData, AuditService, AuditServiceInterface } from "../../services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { Component, ViewChild, WritableSignal, inject, linkedSignal } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
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
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { TableUtilsService, TableUtilsServiceInterface } from "../../services/table-utils/table-utils.service";

import { ClearableInputComponent } from "../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../shared/copy-button/copy-button.component";
import { FormsModule } from "@angular/forms";
import { KeywordFilterComponent } from "../shared/keyword-filter/keyword-filter.component";
import { MatCardModule } from "@angular/material/card";
import { MatInput } from "@angular/material/input";
import { NgClass } from "@angular/common";
import { RouterLink } from "@angular/router";
import { ScrollToTopDirective } from "../shared/directives/app-scroll-to-top.directive";

const columnKeysMap = [
  { key: "number", label: "Number" },
  { key: "action", label: "Action" },
  { key: "success", label: "Success" },
  { key: "authentication", label: "Authentication" },
  { key: "serial", label: "Serial" },
  { key: "container_serial", label: "Container Serial" },
  { key: "startdate", label: "Start Date" },
  { key: "duration", label: "Duration" },
  { key: "token_type", label: "Token Type" },
  { key: "user", label: "User" },
  { key: "realm", label: "Realm" },
  { key: "administrator", label: "Administrator" },
  { key: "action_detail", label: "Action Detail" },
  { key: "info", label: "Info" },
  { key: "policies", label: "Policies" },
  { key: "client", label: "Client" },
  { key: "user_agent", label: "User Agent" },
  { key: "user_agent_version", label: "User Agent Version" },
  { key: "privacyidea_server", label: "PrivacyIDEA Server" },
  { key: "log_level", label: "Log Level" },
  { key: "clearance_level", label: "Clearance Level" },
  { key: "sig_check", label: "Signature Check" },
  { key: "missing_line", label: "Missing Line" },
  { key: "resolver", label: "Resolver" },
  { key: "thread_id", label: "Thread ID" },
  { key: "container_type", label: "Container Type" }
];

@Component({
  selector: "app-audit",
  imports: [
    MatCardModule,
    KeywordFilterComponent,
    MatCell,
    MatFormField,
    FormsModule,
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
    CopyButtonComponent,
    RouterLink,
    ScrollToTopDirective,
    ClearableInputComponent,
    RouterLink
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
  @ViewChild("filterHTMLInputElement", { static: true })
  filterInput!: HTMLInputElement;
  totalLength: WritableSignal<number> = linkedSignal({
    source: this.auditService.auditResource.value,
    computation: (auditResource, previous) => {
      if (auditResource) {
        return auditResource.result?.value?.count ?? 0;
      }
      return previous?.value ?? 0;
    }
  });
  emptyResource: WritableSignal<AuditData[]> = linkedSignal({
    source: this.auditService.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => Object.fromEntries(this.columnKeysMap.map((col) => [col.key, ""])))
  });
  auditDataSource: WritableSignal<MatTableDataSource<AuditData>> = linkedSignal({
    source: this.auditService.auditResource.value,
    computation: (auditResource, previous) => {
      if (auditResource) {
        return new MatTableDataSource(auditResource.result?.value?.auditdata);
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    }
  });
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  onPageEvent(event: PageEvent) {
    this.auditService.pageSize.set(event.pageSize);
    this.auditService.pageIndex.set(event.pageIndex);
  }
}
