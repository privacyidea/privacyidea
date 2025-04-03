import {
  Component,
  effect,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MachineService } from '../../../../services/machine/machine.service';
import { TokenSelectedContent } from '../../token.component';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';

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
  ],
  templateUrl: './token-applications-offline.html',
  styleUrls: ['./token-applications-offline.scss'],
})
export class TokenApplicationsOffline {
  static columnsKeyMap = columnsKeyMap;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input()
  selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() length!: WritableSignal<number>;
  @Input() pageSize!: WritableSignal<number>;
  @Input() pageIndex!: WritableSignal<number>;
  @Input() filterValue!: WritableSignal<string>;
  @Input() sortby_sortdir!: WritableSignal<Sort>;
  @Input() fetchApplicationOfflineData!: (filter?: string) => void;
  @Input() tokenSelected!: (serial: string) => void;
  @Input() dataSource!: WritableSignal<MatTableDataSource<any>>;
  clickedKeyword = signal<string>('');
  columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = columnsKeyMap.map((c) => c.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.machineService.offlineApiFilter;
  advancedApiFilter = this.machineService.offlineAdvancedApiFilter;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('filterInput', { static: true })
  filterInput!: HTMLInputElement;
  filterSubject = new Subject<string>();

  constructor(
    protected tableUtilsService: TableUtilsService,
    private machineService: MachineService,
  ) {
    effect(() => {
      this.filterSubject.next(this.filterValue());
    });
  }

  ngOnInit() {
    this.filterSubject
      .pipe(distinctUntilChanged(), debounceTime(200))
      .subscribe((filter) => {
        this.fetchApplicationOfflineData(filter);
      });
  }

  onFilterChange(newFilter: string) {
    this.filterValue.set(newFilter);
    this.pageIndex.set(0);
  }
}
