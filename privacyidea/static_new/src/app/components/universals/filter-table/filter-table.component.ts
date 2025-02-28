import {
  Component,
  signal,
  WritableSignal,
  Input,
  ViewChild,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';

import { MatSort, MatSortModule } from '@angular/material/sort';
import { AuthService } from '../../../services/auth/auth.service';
import { Router } from '@angular/router';
import { NgClass } from '@angular/common';
import { MatIcon } from '@angular/material/icon';
import { MatFabButton } from '@angular/material/button';
import { NotificationService } from '../../../services/notification/notification.service';
import { KeywordFilter } from '../../../services/keyword_filter';
import {
  OnClickTableColumn,
  TableColumn,
} from '../../../services/table-utils/table-column';
import { Observable } from 'rxjs';

export type FetchDataHandler = (named: {
  pageIndex: number;
  pageSize: number;
  sortby_sortdir: SortDir;
  filterValue: string;
}) => Observable<any>;

export type ProcessDataSource<T> = (
  response: any,
) => [number, MatTableDataSource<T>];

export type FetchErrorHandler = (error: any) => void;

export type SortDir =
  | { active: string; direction: 'asc' | 'desc' | '' }
  | undefined;

@Component({
  selector: 'app-filter-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    MatPaginatorModule,
    MatTableModule,
    MatSortModule,
    NgClass,
    MatIcon,
    MatFabButton,
  ],
  templateUrl: './filter-table.component.html',
  styleUrls: ['./filter-table.component.scss'],
})
export class FilterTable<T> {
  @Input({ required: true }) columns!: TableColumn<any>[];
  @Input({ required: true }) basicFilters!: KeywordFilter[];
  @Input({ required: true }) fetchDataHandler!: FetchDataHandler;
  @Input({ required: true }) processDataSource!: ProcessDataSource<T>;
  @Input() advancedFilters: KeywordFilter[] = [];

  // Uses the handler to toggle the keyword in the filter, when no handler is found, the default handler is used. (add/remove the keyword)
  @Input() pageSizeOptions = [10, 25, 50, 100];
  @Input() fetchErrorHandler: (error: any) => void = (error) => {
    console.error(error);
  };

  numItems: number = 0;
  pageSize: number = 10;
  pageIndex: number = 0;
  filterValue: string = '';
  showAdvancedFilter: WritableSignal<boolean> = signal(false);

  // Must be set in ngOnInit
  filters!: KeywordFilter[];
  displayedColumns!: string[];
  dataSource!: WritableSignal<MatTableDataSource<any>>;

  sortby_sortdir:
    | { active: string; direction: 'asc' | 'desc' | '' }
    | undefined;

  @ViewChild(MatSort) sort!: MatSort;

  constructor(
    private authService: AuthService,
    private router: Router,
    private notificationService: NotificationService,
  ) {}

  ngOnInit(): void {
    this.filters = this.basicFilters.concat(this.advancedFilters);
    this.displayedColumns = this.columns.map((column) => column.key);
    this.dataSource = signal(
      new MatTableDataSource(
        Array.from({ length: this.pageSize }, () => {
          const emptyRow: any = {};
          this.columns.forEach((column) => {
            emptyRow[column.key] = '';
          });
          return emptyRow;
        }),
      ),
    );
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then((r) => {
        console.warn('Redirected to login page.', r);
        this.notificationService.openSnackBar('Redirected to login page.');
      });
    } else {
      this.fetchData();
    }
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.pageIndex = 0;
    this.fetchData();
  }

  handlePageEvent(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.fetchData();
  }

  handleSortEvent() {
    const sort = this.sort;
    this.sortby_sortdir = sort
      ? {
          active: sort.active,
          direction: sort.direction,
        }
      : undefined;
    this.pageIndex = 0;
    this.fetchData();
  }

  private fetchData() {
    this.fetchDataHandler({
      pageIndex: this.pageIndex,
      pageSize: this.pageSize,
      sortby_sortdir: this.sortby_sortdir,
      filterValue: this.filterValue,
    }).subscribe({
      next: (response) => {
        const [numItems, dataSource] = this.processDataSource(response);
        this.numItems = numItems;
        this.dataSource.set(dataSource);
      },
      error: this.fetchErrorHandler,
    });
  }
  handleOnClick(element: any, column: TableColumn<any>) {
    if (column instanceof OnClickTableColumn) {
      var observable = column.onClick(element);
      if (observable) {
        observable.subscribe({
          next: () => {
            this.fetchData();
          },
        });
      } else {
        this.fetchData();
      }
    }
  }

  toggleKeyword(keywordFilter: KeywordFilter, htmlElement: HTMLElement): void {
    htmlElement.focus();
    this.filterValue = keywordFilter.toggleKeyword(this.filterValue);
    this.fetchData();
  }
}
