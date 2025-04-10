import {
  Component,
  effect,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { TokenSelectedContent } from '../../token.component';
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
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';

export const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'serviceid', label: 'Service ID' },
  { key: 'ssh_user', label: 'SSH User' },
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
  ],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
  static columnsKeyMap = columnsKeyMap;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() length!: WritableSignal<number>;
  @Input() pageSize!: WritableSignal<number>;
  @Input() pageIndex!: WritableSignal<number>;
  @Input() filterValue!: WritableSignal<string>;
  @Input() sortby_sortdir!: WritableSignal<Sort>;
  @Input() dataSource!: WritableSignal<MatTableDataSource<any>>;
  @Input() fetchApplicationSshData!: (filter?: string) => void;
  @Input() tokenSelected!: (serial: string) => void;
  clickedKeyword = signal<string>('');
  columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.machineService.sshApiFilter;
  advancedApiFilter = this.machineService.sshAdvancedApiFilter;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('filterInput', { static: true })
  filterInput!: HTMLInputElement;
  filterSubject = new Subject<string>();

  constructor(
    private machineService: MachineService,
    protected tableUtilsService: TableUtilsService,
  ) {
    effect(() => {
      this.filterSubject.next(this.filterValue());
    });
  }

  ngOnInit() {
    this.filterSubject
      .pipe(distinctUntilChanged(), debounceTime(200))
      .subscribe((filter) => {
        this.fetchApplicationSshData(filter);
      });
  }

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }

  onFilterChange(newFilter: string) {
    this.filterValue.set(newFilter);
    this.pageIndex.set(0);
  }
}
