import { Component, computed } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule, Sort } from '@angular/material/sort';
import {
  MachineService,
  TokenApplication,
} from '../../../../services/machine/machine.service';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { TokenService } from '../../../../services/token/token.service';
import { FormsModule } from '@angular/forms';
import { ContentService } from '../../../../services/content/content.service';

const _offlineColumnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'count', label: 'Count' },
  { key: 'rounds', label: 'Rounds' },
];

@Component({
  selector: 'app-token-applications-offline',
  standalone: true,
  imports: [
    MatTabsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    KeywordFilterComponent,
    MatFormField,
    MatInput,
    MatLabel,
    NgClass,
    CopyButtonComponent,
    FormsModule,
  ],
  templateUrl: './token-applications-offline.component.html',
  styleUrls: ['./token-applications-offline.component.scss'],
})
export class TokenApplicationsOfflineComponent {
  columnsKeyMap = _offlineColumnsKeyMap;
  pageSizeOptions = [5, 10, 15];
  length = computed(() => this.machineService.tokenApplications()?.length ?? 0);
  displayedColumns: string[] = _offlineColumnsKeyMap.map(
    (column) => column.key,
  );

  constructor(
    protected machineService: MachineService,
    protected tableUtilsService: TableUtilsService,
    protected tokenService: TokenService,
    protected contentService: ContentService,
  ) {}

  dataSource = computed(() => {
    var data = this.machineService.tokenApplications();
    if (data) {
      return new MatTableDataSource<TokenApplication>(data);
    }
    return this.tableUtilsService.emptyDataSource(
      this.machineService.pageSize(),
      _offlineColumnsKeyMap,
    );
  });

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }
}
