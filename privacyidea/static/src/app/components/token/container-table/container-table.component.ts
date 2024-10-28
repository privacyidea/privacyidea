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
import {HttpClient} from '@angular/common/http';

const columns = [
  {key: 'serial', label: 'Serial'},
  {key: 'type', label: 'Type'},
  {key: 'description', label: 'Description'},
  {key: 'users', label: 'User'},
  {key: 'user_realms', label: 'Realm'},
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
  private headerDict = {headers: {'PI-Authorization': localStorage.getItem('bearer_token') || ''}}
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

  constructor(private authService: AuthService, private router: Router, private http: HttpClient) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.log('Redirected to login page', r));
    }

    this.http.get('http://127.0.0.1:5000/container', this.headerDict).subscribe({
      next: (response: any) => {
        console.log('Container data', response.result.value.containers); // TODO map values correctly and remove this line
        const containers = response.result.value.containers;
        this.length = containers.length;
        this.fullData = containers;
        this.currentData = containers;
        this.updateDataSource(this.currentData);
      }, error: (error: any) => {
        console.error('Failed to get container data', error);
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  applyFilter(event: Event) {
    const filterValue = String((event.target as HTMLInputElement).value).trim().toLowerCase();
    const filterKeys = columns.map((column) => column.key);
    this.currentData = this.fullData.filter((item) => {
      return filterKeys.some((key) => {
        const value = String(item[key]).trim().toLowerCase();
        if (filterValue === 'false' && item[key] === false) {  // special case for boolean value 'false'
          return true;
        }
        if (value.includes(filterValue)) {
          console.log('Matched', key, value);
        }
        return value.includes(filterValue);
      });
    });
    console.log('Filtered data', this.currentData);

    this.pageIndex = 0;
    this.length = this.currentData.length;
    this.updateDataSource(this.currentData);
  }

  sortData(sort: Sort) {
    if (!sort.active || sort.direction === '') {
      this.updateDataSource(this.currentData);
      return;
    }

    function compare(a: string | number, b: string | number, isAsc: boolean) {
      return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
    }

    this.currentData = this.currentData.slice().sort((a: any, b: any) => {
      const isAsc = sort.direction === 'asc';
      switch (sort.active) {
        case 'serial':
          return compare(a.serial, b.serial, isAsc);
        case 'type':
          return compare(a.type, b.type, isAsc);
        case 'description':
          return compare(a.description, b.description, isAsc);
        case 'users':
          return compare(a.users, b.users, isAsc);
        case 'user_realms':
          return compare(a.user_realms, b.user_realms, isAsc);
        case 'realms':
          return compare(a.realms, b.realms, isAsc);
        default:
          return 0;
      }
    });

    this.pageIndex = 0;
    this.updateDataSource(this.currentData);
  }

  pageEvent: PageEvent | undefined;

  handlePageEvent(e: PageEvent) {
    this.pageEvent = e;
    this.pageSize = e.pageSize;
    this.pageIndex = e.pageIndex;
    this.updateDataSource(this.currentData);
  }

  private updateDataSource(data: any[]) {
    const startIndex = this.pageIndex * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    const processedData = data.slice(startIndex, endIndex).map((item) => ({
      ...item,
      users: item.users && item.users.length > 0 ? item.users[0]["user_name"] : ''
    }));

    this.dataSource.set(new MatTableDataSource(processedData.slice(startIndex, endIndex)));
  }

  protected readonly columns = columns;
}
