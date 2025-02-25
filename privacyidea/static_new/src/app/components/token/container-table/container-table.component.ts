import {
  Component,
  Input,
  signal,
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
import { MatSort, MatSortModule } from '@angular/material/sort';
import { AuthService } from '../../../services/auth/auth.service';
import { Router } from '@angular/router';
import { ContainerService } from '../../../services/container/container.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';
import {
  FetchDataHandler,
  FetchResponseHandler,
  FilterTable,
  SortDir,
} from '../../universals/filter-table/filter-table.component';
import {
  OnClickTableColumn,
  SimpleTableColumn,
  TableColumn,
} from '../../../services/table-utils/table-column';
import { KeywordFilter } from '../../../services/keyword_filter';

@Component({
  selector: 'app-container-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    FilterTable,
  ],
  templateUrl: './container-table.component.html',
  styleUrl: './container-table.component.scss',
})
export class ContainerTableComponent {
  columns: TableColumn<any>[] = [
    new OnClickTableColumn<string>({
      key: 'serial',
      label: 'Serial',
      getItems: (value) => [value],
      onClick: (value) => this.containerSelected(value),
    }),
    new SimpleTableColumn<string>({
      key: 'type',
      label: 'Type',
      getItems: (value) => [value],
    }),
    new SimpleTableColumn<string>({
      key: 'states',
      label: 'Status',
      getItems: (value) => [value],
    }),
    new SimpleTableColumn<string>({
      key: 'description',
      label: 'Description',
      getItems: (value) => [value],
    }),
    new SimpleTableColumn<string>({
      key: 'users',
      label: 'User',
      getItems: (value) => [value],
    }),
    new SimpleTableColumn<string>({
      key: 'user_realm',
      label: 'Realm',
      getItems: (value) => [value],
    }),
    new SimpleTableColumn<string>({
      key: 'realms',
      label: 'Container Realms',
      getItems: (value) => [value],
    }),
  ];
  length = 0;
  pageSize = 10;
  pageIndex = 0;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';

  basicFilters: KeywordFilter[] = [
    new KeywordFilter({ key: 'container_serial', label: 'Serial' }),
    new KeywordFilter({ key: 'type', label: 'Type' }),
    new KeywordFilter({ key: 'user', label: 'User' }),
  ];
  advancedFilters: KeywordFilter[] = [
    new KeywordFilter({ key: 'token_serial', label: 'Token Serial' }),
  ];
  fetchDataHandler: FetchDataHandler = ({
    pageIndex,
    pageSize,
    sortby_sortdir,
    filterValue,
  }) => {
    return this.containerService.getContainerData(
      pageIndex,
      pageSize,
      sortby_sortdir,
      filterValue,
    );
  };
  fetchResponseHandler: FetchResponseHandler = (response: any) => {
    return [response.result.value.count, response.result.value.containers];
  };

  sortby_sortdir: SortDir;
  @Input() selectedContent!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  dataSource = signal(new MatTableDataSource<any>());
  showAdvancedFilter = signal(false);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  constructor(
    private router: Router,
    private authService: AuthService,
    private containerService: ContainerService,
    private notificationService: NotificationService,
    protected tableUtilsService: TableUtilsService,
  ) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then((r) => {
        console.warn('Redirected to login page.', r);
        this.notificationService.openSnackBar('Redirected to login page.');
      });
    } else {
      this.fetchContainerData();
    }
  }

  ngAfterViewInit() {
    this.dataSource.set(
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
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  handlePageEvent(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.fetchContainerData();
  }

  handleSortEvent() {
    this.sortby_sortdir = this.sort
      ? {
          active: this.sort.active,
          direction: this.sort.direction,
        }
      : undefined;
    this.pageIndex = 0;
    this.fetchContainerData();
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.pageIndex = 0;
    this.fetchContainerData();
  }

  // toggleKeywordInFilter(keyword: string, inputElement: HTMLInputElement): void {
  //   inputElement.value = this.tableUtilsService.toggleKeywordInFilter(
  //     inputElement.value.trim(),
  //     keyword,
  //   );
  //   this.handleFilterInput({
  //     target: inputElement,
  //   } as unknown as KeyboardEvent);
  //   inputElement.focus();
  // }

  handleStateClick(element: any) {
    this.containerService
      .toggleActive(element.serial, element.states)
      .subscribe({
        next: () => {
          this.fetchContainerData();
        },
        error: (error) => {
          console.error('Failed to toggle active.', error);
          this.notificationService.openSnackBar('Failed to toggle active.');
        },
      });
  }

  containerSelected(containerSerial: string) {
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }

  private fetchContainerData() {
    this.containerService
      .getContainerData(
        this.pageIndex + 1,
        this.pageSize,
        this.sortby_sortdir,
        this.filterValue,
      )
      .subscribe({
        next: (response) => {
          this.length = response.result.value.count;
          this.processDataSource(response.result.value.containers);
        },
        error: (error) => {
          console.error('Failed to get container data.', error);
          this.notificationService.openSnackBar(
            'Failed to get container data.',
          );
        },
      });
  }

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
