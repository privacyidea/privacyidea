import { NgClass } from '@angular/common';
import { Component, computed, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../../services/content/content.service';
import {
  MachineService,
  MachineServiceInterface,
  TokenApplication,
} from '../../../../services/machine/machine.service';
import {
  TableUtilsService,
  TableUtilsServiceInterface,
} from '../../../../services/table-utils/table-utils.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../../services/token/token.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';

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
    @Inject(MachineService)
    protected machineService: MachineServiceInterface,
    @Inject(TableUtilsService)
    protected tableUtilsService: TableUtilsServiceInterface,
    @Inject(TokenService)
    protected tokenService: TokenServiceInterface,
    @Inject(ContentService)
    protected contentService: ContentServiceInterface,
  ) {}

  dataSource = computed(() => {
    var data = this.machineService.tokenApplications();
    if (data.length) {
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
