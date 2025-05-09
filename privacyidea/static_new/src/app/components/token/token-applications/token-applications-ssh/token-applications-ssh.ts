import { Component, Input, ViewChild, WritableSignal } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MachineService } from '../../../../services/machine/machine.service';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import {
  MatCell,
  MatCellDef,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { MatFormField, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule, Sort } from '@angular/material/sort';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { TokenService } from '../../../../services/token/token.service';
import { FormsModule } from '@angular/forms';
import { ContentService } from '../../../../services/content/content.service';

export const columnsKeyMap = [
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
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
  static columnsKeyMap = columnsKeyMap;
  tokenSerial = this.tokenService.tokenSerial;
  selectedContent = this.contentService.selectedContent;
  @Input() length!: WritableSignal<number>;
  @Input() pageSize!: WritableSignal<number>;
  @Input() pageIndex!: WritableSignal<number>;
  @Input() filterValue!: WritableSignal<string>;
  @Input() sort!: WritableSignal<Sort>;
  @Input() dataSource!: WritableSignal<MatTableDataSource<any>>;
  columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.machineService.sshApiFilter;
  advancedApiFilter = this.machineService.sshAdvancedApiFilter;
  @ViewChild('filterInput', { static: true })
  filterInput!: HTMLInputElement;

  constructor(
    protected machineService: MachineService,
    protected tableUtilsService: TableUtilsService,
    protected tokenService: TokenService,
    protected contentService: ContentService,
  ) {}

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }
}
