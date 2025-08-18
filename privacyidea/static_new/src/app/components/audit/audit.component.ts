import { NgClass } from "@angular/common";
import { Component, effect, inject, linkedSignal, ViewChild, WritableSignal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatCardModule } from "@angular/material/card";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
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
import { AuditData, AuditService, AuditServiceInterface } from "../../services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "../../services/content/content.service";
import {
  TableUtilsService,
  TableUtilsServiceInterface
} from "../../services/table-utils/table-utils.service";
import { CopyButtonComponent } from "../shared/copy-button/copy-button.component";
import { KeywordFilterComponent } from "../shared/keyword-filter/keyword-filter.component";

const columnKeysMap = [
  { key: "number", label: "Number" },
  { key: "action", label: "Action" },
  { key: "success", label: "Success" },
  { key: "authentication", label: "Authentication" },
  { key: "serial", label: "Serial" },
  { key: "container_serial", label: "Container Serial" },
  { key: "date", label: "End Date" },
  { key: "startdate", label: "Start Date" },
  { key: "duration", label: "Duration" },
  { key: "token_type", label: "Token Type" },
  { key: "user", label: "User" },
  { key: "realm", label: "Realm" },
  { key: "administrator", label: "Administrator" },
  { key: "action_detail", label: "Action Detail" },
  { key: "info", label: "Info" },
  { key: "privacyidea_server", label: "PrivacyIDEA Server" },
  { key: "client", label: "Client" },
  { key: "user_agent", label: "User Agent" },
  { key: "user_agent_version", label: "User Agent Version" },
  { key: "log_level", label: "Log Level" },
  { key: "policies", label: "Policies" },
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
    RouterLink
  ],
  templateUrl: "./audit.component.html",
  styleUrl: "./audit.component.scss"
})
export class AuditComponent {
  protected readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly tableUtilsService: TableUtilsServiceInterface =
    inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map(
    (column) => column.key
  );

  filterValueString: WritableSignal<string> = linkedSignal(() =>
    Object.entries(this.auditService.filterValue())
      .map(([key, value]) => `${key}: ${value}`)
      .join(" ")
  );
  totalLength: WritableSignal<number> = linkedSignal({
    source: this.auditService.auditResource.value,
    computation: (auditResource, previous) => {
      if (auditResource) {
        return auditResource.result?.value?.count ?? 0;
      }
      return previous?.value ?? 0;
    }
  });
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;

  emptyResource: WritableSignal<AuditData[]> = linkedSignal({
    source: this.auditService.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () =>
        Object.fromEntries(this.columnKeysMap.map((col) => [col.key, ""]))
      )
  });

  auditDataSource: WritableSignal<MatTableDataSource<AuditData>> = linkedSignal(
    {
      source: this.auditService.auditResource.value,
      computation: (auditResource, previous) => {
        if (auditResource) {
          return new MatTableDataSource(auditResource.result?.value?.auditdata);
        }
        return previous?.value ?? new MatTableDataSource(this.emptyResource());
      }
    }
  );

  @ViewChild("filterHTMLInputElement", { static: true })
  filterInput!: HTMLInputElement;

  constructor() {
    effect(() => {
      const filterValueString = this.filterValueString();
      const recordsFromText =
        this.tableUtilsService.recordsFromText(filterValueString);
      if (this.filterInput) {
        this.filterInput.value = filterValueString;
      }
      if (
        JSON.stringify(this.auditService.filterValue()) !==
        JSON.stringify(recordsFromText)
      ) {
        this.auditService.filterValue.set(recordsFromText);
      }
      this.auditService.pageIndex.set(0);
    });
  }

  onPageEvent(event: PageEvent) {
    this.auditService.pageSize.set(event.pageSize);
    this.auditService.pageIndex.set(event.pageIndex);
  }
}
