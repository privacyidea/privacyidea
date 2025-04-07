import {
  Component,
  effect,
  Input,
  linkedSignal,
  signal,
  untracked,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import {
  MatPaginator,
  MatPaginatorModule,
  PageEvent,
} from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { NgClass } from '@angular/common';
import { TokenService } from '../../../services/token/token.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { TokenSelectedContent } from '../token.component';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';
import { MatCheckboxModule } from '@angular/material/checkbox';

const columnsKeyMap = [
  { key: 'select', label: '' },
  { key: 'serial', label: 'Serial' },
  { key: 'tokentype', label: 'Type' },
  { key: 'active', label: 'Active' },
  { key: 'description', label: 'Description' },
  { key: 'failcount', label: 'Fail Counter' },
  { key: 'rollout_state', label: 'Rollout State' },
  { key: 'username', label: 'User' },
  { key: 'user_realm', label: 'User Realm' },
  { key: 'realms', label: 'Token Realm' },
  { key: 'container_serial', label: 'Container' },
];

@Component({
  selector: 'app-token-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    KeywordFilterComponent,
    CopyButtonComponent,
    MatCheckboxModule,
  ],
  templateUrl: './token-table.component.html',
  styleUrl: './token-table.component.scss',
})
export class TokenTableComponent {
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  apiFilter = this.tokenService.apiFilter;
  advancedApiFilter = this.tokenService.advancedApiFilter;
  columnsKeyMap = columnsKeyMap;
  sortby_sortdir: WritableSignal<Sort> = signal({
    active: 'serial',
    direction: 'asc',
  });
  length = signal(0);
  pageSize = signal(10);
  pageIndex = signal(0);
  filterValue = signal('');
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() tokenSelection!: WritableSignal<any[]>;
  @Input() refreshTokenOverview!: WritableSignal<boolean>;
  dataSource = signal(
    new MatTableDataSource(
      Array.from({ length: this.pageSize() }, () => {
        const emptyRow: any = {};
        columnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
    ),
  );
  pageSizeOptions = linkedSignal({
    source: this.length,
    computation: (length) =>
      [5, 10, 15].includes(length) ? [5, 10, 15] : [5, 10, 15, length],
  });
  clickedKeyword = signal<string>('');
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('filterInput', { static: true }) filterInput!: HTMLInputElement;
  filterSubject = new Subject<string>();

  constructor(
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
  ) {
    effect(() => {
      this.filterSubject.next(this.filterValue());
      this.tokenSelection.set([]);
      untracked(() => {
        if (![5, 10, 15].includes(this.pageSize())) {
          this.pageSize.set(10);
        }
        this.pageIndex.set(0);
      });
    });
    effect(() => {
      if (this.selectedContent()) {
        this.tokenSelection.set([]);
      }
    });
  }

  ngOnInit() {
    this.filterSubject
      .pipe(distinctUntilChanged(), debounceTime(200))
      .subscribe((filter) => {
        this.fetchTokenData(filter);
      });
  }

  onFilterChange(newFilter: string) {
    this.filterValue.set(newFilter);
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  isAllSelected() {
    return this.tokenSelection().length === this.dataSource().data.length;
  }

  toggleAllRows() {
    if (this.isAllSelected()) {
      this.tokenSelection.set([]);
    } else {
      this.tokenSelection.set([...this.dataSource().data]);
    }
  }

  toggleRow(row: any): void {
    const current = this.tokenSelection();
    if (current.includes(row)) {
      this.tokenSelection.set(current.filter((r) => r !== row));
    } else {
      this.tokenSelection.set([...current, row]);
    }
  }

  checkboxLabel(row?: any): string {
    if (!row) {
      return `${this.isAllSelected() ? 'deselect' : 'select'} all`;
    }
    return `${
      this.tokenSelection().includes(row) ? 'deselect' : 'select'
    } row ${row.position + 1}`;
  }

  toggleActive(element: any): void {
    this.tokenService.toggleActive(element.serial, element.active).subscribe({
      next: () => {
        this.fetchTokenData();
      },
    });
  }

  resetFailCount(element: any): void {
    this.tokenService.resetFailCount(element.serial).subscribe({
      next: () => {
        this.fetchTokenData();
      },
    });
  }

  handleColumnClick(columnKey: string, element: any): void {
    if (element.revoked || element.locked) {
      return;
    }
    switch (columnKey) {
      case 'active':
        this.toggleActive(element);
        break;
      case 'failcount':
        this.resetFailCount(element);
        break;
    }
  }

  tokenSelected(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  containerSelected(containerSerial: string) {
    this.isProgrammaticChange.set(true);
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }

  onPageEvent(event: PageEvent) {
    this.tokenSelection.set([]);
    this.tableUtilsService.handlePageEvent(
      event,
      this.pageIndex,
      this.pageSize,
      this.fetchTokenData,
    );
  }

  onSortEvent($event: Sort) {
    this.tokenSelection.set([]);
    this.tableUtilsService.handleSortEvent(
      $event,
      this.pageIndex,
      this.sortby_sortdir,
      this.fetchTokenData,
    );
  }

  fetchTokenData = (filterValue?: string) => {
    return this.tokenService
      .getTokenData(
        this.pageIndex() + 1,
        this.pageSize(),
        this.sortby_sortdir(),
        filterValue ?? this.filterValue(),
      )
      .subscribe({
        next: (response) => {
          this.length.set(response.result.value.count);
          this.dataSource.set(
            new MatTableDataSource(response.result.value.tokens),
          );
        },
      });
  };
}
