import {
  Component,
  Input,
  Signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MachineService } from '../../../../services/machine/machine.service';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { TokenService } from '../../../../services/token/token.service';
import { FormsModule } from '@angular/forms';

export const columnsKeyMap = [
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
  templateUrl: './token-applications-offline.html',
  styleUrls: ['./token-applications-offline.scss'],
})
export class TokenApplicationsOffline {
  static columnsKeyMap = columnsKeyMap;
  tokenSerial = this.tokenService.tokenSerial;
  selectedContent = this.tokenService.selectedContent;
  @Input() length!: WritableSignal<number>;
  @Input() pageSize!: WritableSignal<number>;
  @Input() pageIndex!: WritableSignal<number>;
  @Input() filterValue!: WritableSignal<string>;
  @Input() sort!: WritableSignal<Sort>;
  @Input() dataSource!: Signal<MatTableDataSource<any>>;
  columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = columnsKeyMap.map((c) => c.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.machineService.offlineApiFilter;
  advancedApiFilter = this.machineService.offlineAdvancedApiFilter;
  @ViewChild('filterInput', { static: true })
  filterInput!: HTMLInputElement;

  constructor(
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    protected machineService: MachineService,
  ) {}

  onFilterChange(newFilter: string) {
    this.filterValue.set(newFilter);
    this.pageIndex.set(0);
  }
}
