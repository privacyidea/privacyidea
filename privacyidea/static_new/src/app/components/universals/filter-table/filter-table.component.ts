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
import { Observable } from 'rxjs';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { AuthService } from '../../../services/auth/auth.service';
import { Router } from '@angular/router';
import { NgClass } from '@angular/common';
import { TokenService } from '../../../services/token/token.service';
import { MatIcon } from '@angular/material/icon';
import { MatFabButton } from '@angular/material/button';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';

export type FetchDataHandler = (
  pageIndex: number,
  pageSize: number,
  sortby_sortdir: SortDir,
  filterValue: string,
) => Observable<any>;

export type FetchResponseHandler = (
  response: any,
) => [number, MatTableDataSource<any>];

export type FetchErrorHandler = (error: any) => void;

export type FilterKeywordHandlerMap = {
  key: string;
  handler: (filterValue: string) => string;
}[];

export type CellClickHandlerMap = {
  key: string;
  handler: (element: any, data?: any) => Observable<any>;
}[];

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
export class FilterTable {
  @Input({ required: true }) columnsKeyMap!: { key: string; label: string }[];

  @Input({ required: true }) apiFilter!: string[];
  @Input({ required: true }) fetchDataHandler!: FetchDataHandler;
  @Input({ required: true }) fetchResponseHandler!: FetchResponseHandler;
  @Input() advancedApiFilter: string[] = [];

  // Uses the handler to toggle the keyword in the filter, when no handler is found, the default handler is used. (add/remove the keyword)
  @Input() filterKeywordHandlerMap: FilterKeywordHandlerMap = [];
  @Input() pageSizeOptions = [10, 25, 50, 100];
  @Input() fetchErrorHandler: FetchErrorHandler = (error) => {
    console.error(error);
  };
  @Input() cellClickHandlerMap: CellClickHandlerMap = [];

  numItems: number = 0;
  pageSize: number = 10;
  pageIndex: number = 0;
  filterValue: string = '';
  showAdvancedFilter: WritableSignal<boolean> = signal(false);

  // Must be set in ngOnInit
  allApiFilter!: string[];
  displayedColumns!: string[];
  dataSource!: WritableSignal<MatTableDataSource<any>>;

  ngOnInit(): void {
    this.allApiFilter = this.apiFilter.concat(this.advancedApiFilter);
    this.displayedColumns = this.columnsKeyMap.map((column) => column.key);
    this.dataSource = signal(
      new MatTableDataSource(
        Array.from({ length: this.pageSize }, () => {
          const emptyRow: any = {};
          this.columnsKeyMap.forEach((column) => {
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

  sortby_sortdir:
    | { active: string; direction: 'asc' | 'desc' | '' }
    | undefined;

  @ViewChild(MatSort) sort!: MatSort;

  constructor(
    private router: Router,
    private authService: AuthService,
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    private notificationService: NotificationService,
  ) {}

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.pageIndex = 0;
    this.fetchData();
  }

  toggleKeywordInFilter(
    filterKeyword: string,
    inputElement: HTMLInputElement,
  ): void {
    var result: string | null = null;
    this.filterKeywordHandlerMap.forEach((handler) => {
      if (handler.key === filterKeyword) {
        result = handler.handler(inputElement.value.trim());
      }
    });
    if (result === null) {
      result = this.tableUtilsService.toggleKeywordInFilter(
        inputElement.value.trim(),
        filterKeyword,
      );
    }

    inputElement.value = result;
    this.handleFilterInput({
      target: inputElement,
    } as unknown as KeyboardEvent);
    inputElement.focus();
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
    this.fetchDataHandler(
      this.pageIndex,
      this.pageSize,
      this.sortby_sortdir,
      this.filterValue,
    ).subscribe({
      next: (response) => {
        const [numItems, dataSource] = this.fetchResponseHandler(response);
        this.numItems = numItems;
        this.dataSource.set(dataSource);
      },
      error: this.fetchErrorHandler,
    });
  }

  onClickHandlerOf(key: string): ((element: any, data?: any) => void) | null {
    var usedHandler: ((element: any, data?: any) => void) | null = null;
    this.cellClickHandlerMap.forEach((handler) => {
      if (handler.key === key) {
        usedHandler = (element: any, data?: any) => {
          handler.handler(element, data).subscribe({
            next: () => {
              this.fetchData();
            },
          });
        };
      }
    });
    return usedHandler;
  }

  isArray(arg0: any): boolean {
    return Array.isArray(arg0);
  }
}
// const columnsKeyMap = [
//   { key: 'serial', label: 'Serial' },
//   { key: 'service_id', label: 'Service ID' },
//   { key: 'user', label: 'SSH user' },
// ];
