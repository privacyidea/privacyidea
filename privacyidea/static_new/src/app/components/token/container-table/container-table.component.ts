import {
  Component,
  effect,
  ElementRef,
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
import { ContainerService } from '../../../services/container/container.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { TokenSelectedContent } from '../token.component';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import { CopyButtonComponent } from '../../shared/copy-button/copy-button.component';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';
import { SelectionModel } from '@angular/cdk/collections';
import { MatCheckbox } from '@angular/material/checkbox';

const columnsKeyMap = [
  { key: 'select', label: '' },
  { key: 'serial', label: 'Serial' },
  { key: 'type', label: 'Type' },
  { key: 'states', label: 'Status' },
  { key: 'description', label: 'Description' },
  { key: 'users', label: 'User' },
  { key: 'user_realm', label: 'Realm' },
  { key: 'realms', label: 'Container Realms' },
];

@Component({
  selector: 'app-container-table',
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
    MatCheckbox,
  ],
  templateUrl: './container-table.component.html',
  styleUrl: './container-table.component.scss',
})
export class ContainerTableComponent {
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() containerSelection!: SelectionModel<any>;
  @Input() refreshContainerOverview!: WritableSignal<boolean>;
  sortby_sortdir: WritableSignal<Sort> = signal({
    active: 'serial',
    direction: 'asc',
  });
  length = signal(0);
  pageSize = signal(10);
  pageIndex = signal(0);
  filterValue = signal('');
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
  clickedKeyword = signal<string>('');
  pageSizeOptions = linkedSignal({
    source: this.length,
    computation: (length) =>
      [5, 10, 15].includes(length) ? [5, 10, 15] : [5, 10, 15, length],
  });
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  apiFilter = this.containerService.apiFilter;
  advancedApiFilter = this.containerService.advancedApiFilter;
  columnsKeyMap = columnsKeyMap;
  @ViewChild('filterInput') inputElement!: ElementRef<HTMLInputElement>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  filterSubject = new Subject<string>();

  constructor(
    private containerService: ContainerService,
    private notificationService: NotificationService,
    protected tableUtilsService: TableUtilsService,
  ) {
    effect(() => {
      this.filterSubject.next(this.filterValue());
      this.containerSelection.clear();
      untracked(() => {
        if (![5, 10, 15].includes(this.pageSize())) {
          this.pageSize.set(10);
        }
        this.pageIndex.set(0);
      });
    });
    effect(() => {
      if (this.selectedContent()) {
        this.containerSelection.clear();
      }
    });
  }

  ngOnInit() {
    this.filterSubject
      .pipe(distinctUntilChanged(), debounceTime(200))
      .subscribe((filter) => {
        this.fetchContainerData(filter);
      });
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  isAllSelected() {
    return (
      this.containerSelection.selected.length === this.dataSource().data.length
    );
  }

  toggleAllRows() {
    if (this.isAllSelected()) {
      this.containerSelection.clear();
      return;
    }

    this.containerSelection.select(...this.dataSource().data);
  }

  checkboxLabel(row?: any): string {
    if (!row) {
      return `${this.isAllSelected() ? 'deselect' : 'select'} all`;
    }
    return `${this.containerSelection.isSelected(row) ? 'deselect' : 'select'} row ${row.position + 1}`;
  }

  onFilterChange(newFilter: string) {
    this.filterValue.set(newFilter);
  }

  handleStateClick(element: any) {
    this.containerService
      .toggleActive(element.serial, element.states)
      .subscribe({
        next: () => {
          this.fetchContainerData();
        },
        error: (error) => {
          console.error('Failed to toggle active.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to toggle active. ' + message,
          );
        },
      });
  }

  containerSelected(containerSerial: string) {
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }

  onPageEvent(event: PageEvent) {
    this.containerSelection.clear();
    this.tableUtilsService.handlePageEvent(
      event,
      this.pageIndex,
      this.pageSize,
      this.fetchContainerData,
    );
  }

  onSortEvent($event: Sort) {
    this.containerSelection.clear();
    this.tableUtilsService.handleSortEvent(
      $event,
      this.pageIndex,
      this.sortby_sortdir,
      this.fetchContainerData,
    );
  }

  fetchContainerData = (filterValue?: string) => {
    return this.containerService
      .getContainerData({
        page: this.pageIndex() + 1,
        pageSize: this.pageSize(),
        sort: this.sortby_sortdir(),
        filterValue: filterValue ?? this.filterValue(),
      })
      .subscribe({
        next: (response) => {
          this.length.set(response.result.value.count);
          this.processDataSource(response.result.value.containers);
        },
      });
  };

  private processDataSource(data: any[]) {
    const processedData = data.map((item) => ({
      ...item,
      users:
        item.users && item.users.length > 0 ? item.users[0]['user_name'] : '',
      user_realm:
        item.users && item.users.length > 0 ? item.users[0]['user_realm'] : '',
    }));
    this.dataSource.set(new MatTableDataSource(processedData));
  }
}
