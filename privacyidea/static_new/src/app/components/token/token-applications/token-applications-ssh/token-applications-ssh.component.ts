import { NgClass } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
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
import { ClearableInputComponent } from '../../../shared/clearable-input/clearable-input.component';
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
    ClearableInputComponent,
  ],
  templateUrl: './token-applications-ssh.component.html',
  styleUrls: ['./token-applications-ssh.component.scss'],
})
export class TokenApplicationsSshComponent {
  protected readonly machineService: MachineServiceInterface =
    inject(MachineService);
  protected readonly tableUtilsService: TableUtilsServiceInterface =
    inject(TableUtilsService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface =
    inject(ContentService);

  columnsKeyMap = _sshColumnsKeyMap;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  length = computed(() => this.machineService.tokenApplications()?.length ?? 0);
  displayedColumns: string[] = _sshColumnsKeyMap.map((column) => column.key);

  dataSource = computed(() => {
    var data = this.machineService.tokenApplications();
    if (data) {
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
