import {Component, signal, ViewChild} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {AuthService} from '../../../services/auth/auth.service';
import {Router} from '@angular/router';
import {NgClass} from '@angular/common';
import {MatCard, MatCardContent} from '@angular/material/card';
import {TokenService} from '../../../services/token/token.service';
import {TableUtilsService} from '../../../services/table-utils/table-utils.service';

const columns = [
  {key: 'serial', label: 'Serial'},
  {key: 'tokentype', label: 'Type'},
  {key: 'active', label: 'Active'},
  {key: 'description', label: 'Description'},
  {key: 'failcount', label: 'Fail Counter'},
  {key: 'rollout_state', label: 'Rollout Status'},
  {key: 'username', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
  {key: 'realms', label: 'Token Realm'},
  {key: 'container_serial', label: 'Container'},
];

@Component({
  selector: 'app-token-table',
  standalone: true,
  imports: [
    MatTableModule, MatFormFieldModule, MatInputModule, MatTableModule, MatPaginatorModule, MatTableModule,
    MatSortModule, MatCard, MatCardContent, NgClass
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
  protected readonly columns = columns;

  constructor(private router: Router,
              private authService: AuthService,
              private tokenService: TokenService,
              private tableUtils: TableUtilsService) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.log('Redirected to login page', r));
    } else {
      this.fetchTokenData();
    }
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
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

  private fetchTokenData() {
    this.tokenService.getTokenData().subscribe({
      next: tokens => {
        this.length = tokens.length;
        this.fullData = tokens;
        this.currentData = tokens;
        this.updateDataSource(this.currentData);
      },
      error: error => {
        console.error('Failed to get token data', error);
      }
    });
  }

  handlePageEvent(e: PageEvent) {
    this.pageSize = e.pageSize;
    this.pageIndex = e.pageIndex;
    this.updateDataSource(this.currentData);
  }

  private updateDataSource(data: any[]) {
    const processedData = data.map((item) => ({
      ...item,
      realms: item.realms && item.realms.length > 0 ? item.realms[0] : ''
    }));
    const paginatedData = this.tableUtils.paginateData(processedData, this.pageIndex, this.pageSize);
    this.dataSource.set(new MatTableDataSource(paginatedData));
  }
}
