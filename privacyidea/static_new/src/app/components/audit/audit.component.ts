import { Component, linkedSignal, WritableSignal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { KeywordFilterComponent } from '../shared/keyword-filter/keyword-filter.component';
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
  MatTableDataSource,
} from '@angular/material/table';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { MatInput } from '@angular/material/input';
import { NgClass } from '@angular/common';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { AuditData, AuditService } from '../../services/audit/audit.service';
import { CopyButtonComponent } from '../shared/copy-button/copy-button.component';
import { ContentService } from '../../services/content/content.service';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth/auth.service';

const columnKeysMap = [
  { key: 'number', label: 'Number' },
  { key: 'action', label: 'Action' },
  { key: 'success', label: 'Success' },
  { key: 'authentication', label: 'Authentication' },
  { key: 'serial', label: 'Serial' },
  { key: 'date', label: 'End Date' },
  { key: 'startdate', label: 'Start Date' },
  { key: 'duration', label: 'Duration' },
  { key: 'token_type', label: 'Token Type' },
  { key: 'user', label: 'User' },
  { key: 'realm', label: 'Realm' },
  { key: 'administrator', label: 'Administrator' },
  { key: 'action_detail', label: 'Action Detail' },
  { key: 'info', label: 'Info' },
  { key: 'privacyidea_server', label: 'PrivacyIDEA Server' },
  { key: 'client', label: 'Client' },
  { key: 'user_agent', label: 'User Agent' },
  { key: 'user_agent_version', label: 'User Agent Version' },
  { key: 'log_level', label: 'Log Level' },
  { key: 'policies', label: 'Policies' },
  { key: 'clearance_level', label: 'Clearance Level' },
  { key: 'sig_check', label: 'Signature Check' },
  { key: 'missing_line', label: 'Missing Line' },
  { key: 'resolver', label: 'Resolver' },
  { key: 'thread_id', label: 'Thread ID' },
  { key: 'container_serial', label: 'Container Serial' },
  { key: 'container_type', label: 'Container Type' },
];

@Component({
  selector: 'app-audit',
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
  ],
  templateUrl: './audit.component.html',
  styleUrl: './audit.component.scss',
})
export class AuditComponent {
  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map(
    (column) => column.key,
  );
  readonly apiFilter = this.auditService.apiFilter;
  readonly advancedApiFilter = this.auditService.advancedApiFilter;
  auditResource = this.auditService.auditResource;
  filterValue = this.auditService.filterValue;
  pageSize = this.auditService.pageSize;
  pageIndex = this.auditService.pageIndex;
  totalLength: WritableSignal<number> = linkedSignal({
    source: this.auditResource.value,
    computation: (auditResource, previous) => {
      if (auditResource) {
        return auditResource.result.value?.count ?? 0;
      }
      return previous?.value ?? 0;
    },
  });
  pageSizeOptions = linkedSignal({
    source: this.totalLength,
    computation: (total) => {
      return [5, 10, 15].includes(total) || total > 50
        ? [5, 10, 15]
        : [5, 10, 15, total];
    },
  });

  emptyResource = linkedSignal({
    source: this.pageSize,
    computation: (pageSize: number) =>
      Array.from({ length: pageSize }, () => {
        const emptyRow: any = {};
        this.columnKeysMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
  });

  auditDataSource: WritableSignal<MatTableDataSource<AuditData>> = linkedSignal(
    {
      source: this.auditResource.value,
      computation: (auditResource, previous) => {
        if (auditResource) {
          return new MatTableDataSource(auditResource.result.value?.auditdata);
        }
        return previous?.value ?? new MatTableDataSource(this.emptyResource());
      },
    },
  );

  constructor(
    private auditService: AuditService,
    protected contentService: ContentService,
    protected authService: AuthService,
  ) {}

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }
}
