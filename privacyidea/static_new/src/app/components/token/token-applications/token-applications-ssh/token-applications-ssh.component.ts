import { NgClass } from '@angular/common';
import { Component, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import {
  MatCell,
  MatCellDef,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { ContentService } from '../../../../services/content/content.service';
import {
  MachineService,
  TokenApplication,
} from '../../../../services/machine/machine.service';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { TokenService } from '../../../../services/token/token.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';

const _sshColumnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'service_id', label: 'Service ID' },
  { key: 'user', label: 'SSH User' },
];

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [
    MatTabsModule,
    KeywordFilterComponent,
    MatCell,
    MatCellDef,
    MatFormField,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    CopyButtonComponent,
    FormsModule,
  ],
  templateUrl: './token-applications-ssh.component.html',
  styleUrls: ['./token-applications-ssh.component.scss'],
})
export class TokenApplicationsSshComponent {
  columnsKeyMap = _sshColumnsKeyMap;
  pageSizeOptions = [5, 10, 15];
  length = computed(() => this.machineService.tokenApplications()?.length ?? 0);
  displayedColumns: string[] = _sshColumnsKeyMap.map((column) => column.key);

  constructor(
    protected machineService: MachineService,
    protected tableUtilsService: TableUtilsService,
    protected tokenService: TokenService,
    protected contentService: ContentService,
  ) {}

  dataSource = computed(() => {
    var data = this.machineService.tokenApplications();
    if (data.length) {
      return new MatTableDataSource<TokenApplication>(data);
    }
    return this.tableUtilsService.emptyDataSource(
      this.machineService.pageSize(),
      _sshColumnsKeyMap,
    );
  });

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }
}
