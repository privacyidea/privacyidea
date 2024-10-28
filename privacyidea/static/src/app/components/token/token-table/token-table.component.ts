import {Component, signal, ViewChild} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {AuthService} from '../../../services/auth/auth.service';
import {Router} from '@angular/router';
import {HttpClient} from '@angular/common/http';
import {NgClass, NgForOf, NgIf} from '@angular/common';
import {MatCard, MatCardContent} from '@angular/material/card';
import {LocalService} from '../../../services/local/local.service';

const columns = [
  {key: 'serial', label: 'Serial'},
  {key: 'tokentype', label: 'Type'},
  {key: 'active', label: 'Active'},
  {key: 'description', label: 'Description'},
  {key: 'failcount', label: 'Fail Counter'},
  {key: 'rollout_state', label: 'Rollout Status'},
  {key: 'username', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
  {key: 'tokengroup', label: 'Token Realm'},
  {key: 'container_serial', label: 'Container'},
];

@Component({
  selector: 'app-token-table',
  standalone: true,
  imports: [
    MatTableModule, MatFormFieldModule, MatInputModule, MatTableModule, MatPaginatorModule, MatTableModule,
    MatSortModule, NgForOf, MatCard, MatCardContent, NgClass, NgIf
  ],
  templateUrl: './token-table.component.html',
  styleUrl: './token-table.component.css'
})
export class TokenTableComponent {
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

  constructor(private router: Router, private http: HttpClient,
              private authService: AuthService, private localStore: LocalService) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.log('Redirected to login page', r));
    }
    const headerDict = {headers: {'PI-Authorization': this.localStore.getData('bearer_token') || ''}}
    this.http.get('http://127.0.0.1:5000/token', headerDict).subscribe({
      next: (response: any) => {
        const tokens = response.result.value.tokens;
        console.log('Token data', tokens); // TODO map values correctly and remove this line
        this.length = tokens.length;
        this.fullData = tokens;
        this.currentData = tokens;
        this.updateDataSource(this.currentData);
      }, error: (error: any) => {
        console.error('Failed to get token data', error);
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
        case 'tokentype':
          return compare(a.tokentype, b.tokentype, isAsc);
        case 'active':
          return compare(a.active, b.active, isAsc);
        case 'description':
          return compare(a.description, b.description, isAsc);
        case 'failcount':
          return compare(a.failcount, b.failcount, isAsc);
        case 'rollout_state':
          return compare(a.rollout_state, b.rollout_state, isAsc);
        case 'username':
          return compare(a.username, b.username, isAsc);
        case 'user_realm':
          return compare(a.user_realm, b.user_realm, isAsc);
        case 'token_realm':
          return compare(a.token_realm, b.token_realm, isAsc);
        case 'container_serial':
          return compare(a.container_serial, b.container_serial, isAsc);
        default:
          return 0;
      }
    });

    this.pageIndex = 0;
    this.updateDataSource(this.currentData);
  }

  protected readonly columns = columns;
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

    this.dataSource.set(new MatTableDataSource(data.slice(startIndex, endIndex)));
  }
}
