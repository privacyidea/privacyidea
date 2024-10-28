import {Component, signal, ViewChild} from '@angular/core';
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource
} from '@angular/material/table';
import {MatFormField, MatLabel} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatPaginator, PageEvent} from '@angular/material/paginator';
import {MatSort, MatSortHeader, Sort} from '@angular/material/sort';
import {NgClass, NgForOf, NgIf} from '@angular/common';
import {AuthService} from '../../../services/auth/auth.service';
import {Router} from '@angular/router';
import {ContainerService} from '../../../services/container/container.service';
import {TableUtilsService} from '../../../services/table-utils/table-utils.service';

const columns = [
  {key: 'serial', label: 'Serial'},
  {key: 'type', label: 'Type'},
  {key: 'description', label: 'Description'},
  {key: 'users', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
  {key: 'realms', label: 'Container Realms'},
];

@Component({
  selector: 'app-container-table',
  standalone: true,
  imports: [
    MatCell,
    MatCellDef,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatHeaderRowDef,
    MatInput,
    MatLabel,
    MatPaginator,
    MatRow,
    MatRowDef,
    MatSort,
    MatSortHeader,
    MatTable,
    NgForOf,
    NgIf,
    MatColumnDef,
    MatHeaderCellDef,
    MatNoDataRow,
    NgClass
  ],
  templateUrl: './container-table.component.html',
  styleUrl: './container-table.component.css'
})
export class ContainerTableComponent {
  dataSource = signal(new MatTableDataSource());
  displayedColumns: string[] = columns.map(column => column.key);
  columnDefinitions = columns;
  length = 0;
  pageSize = 10;
  pageIndex = 0;
  hidePageSize = false;
  pageSizeOptions = [5, 10, 15, 20];
  showPageSizeOptions = false;
  disabled = false;

  @ViewChild(MatPaginator) paginator: MatPaginator | null = null;
  @ViewChild(MatSort) sort: MatSort | null = null;
  private fullData: any[] = [];
  private currentData: any[] = [];
  protected readonly columns = columns;

  constructor(private router: Router,
              private authService: AuthService,
              private containerService: ContainerService,
              private tableUtils: TableUtilsService) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.log('Redirected to login page', r));
    } else {
      this.fetchContainerData();
    }
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  private fetchContainerData() {
    this.containerService.getContainerData().subscribe({
      next: containers => {
        this.length = containers.length;
        this.fullData = containers;
        this.currentData = containers;
        this.updateDataSource(this.currentData);
      },
      error: error => {
        console.error('Failed to get container data', error);
      }
    });
  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.currentData = this.tableUtils.applyFilter(this.fullData, filterValue, columns);
    this.updateDataSource(this.currentData);
    this.pageIndex = 0;
    this.length = this.currentData.length;
  }

  sortData(sort: Sort) {
    this.currentData = this.tableUtils.sortData(this.currentData, sort, columns);
    this.updateDataSource(this.currentData);
    this.pageIndex = 0;
  }

  handlePageEvent(e: PageEvent) {
    this.pageSize = e.pageSize;
    this.pageIndex = e.pageIndex;
    this.updateDataSource(this.currentData);
  }

  private updateDataSource(data: any[]) {
    const processedData = data.map((item) => ({
      ...item,
      users: item.users && item.users.length > 0 ? item.users[0]["user_name"] : '',
      user_realm: item.users && item.users.length > 0 ? item.users[0]["user_realm"] : '',
    }));
    const paginatedData = this.tableUtils.paginateData(processedData, this.pageIndex, this.pageSize);
    this.dataSource.set(new MatTableDataSource(paginatedData));
  }
}
