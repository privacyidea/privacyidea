import {Component, signal, ViewChild} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule} from '@angular/material/sort';
import {AuthService} from '../../../services/auth/auth.service';
import {Router} from '@angular/router';
import {NgClass} from '@angular/common';
import {MatCard, MatCardContent} from '@angular/material/card';
import {TokenService} from '../../../services/token/token.service';

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
  pageSizeOptions = [10];
  filterValue = '';

  @ViewChild(MatPaginator) paginator: MatPaginator | null = null;
  @ViewChild(MatSort) sort: MatSort | null = null;
  protected readonly columns = columns;

  constructor(private router: Router,
              private authService: AuthService,
              private tokenService: TokenService) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.log('Redirected to login page', r));
    } else {
      this.fetchTokenData();
    }
  }

  ngAfterViewInit() {
    if (this.paginator) {
      this.paginator.page.subscribe((event: PageEvent) => this.handlePageEvent(event));
    }
    if (this.sort) {
      this.sort.sortChange.subscribe(() => this.handleSortEvent());
    }
  }

  private fetchTokenData() {
    let sort = this.sort ? {active: this.sort.active, direction: this.sort.direction} : undefined;
    this.tokenService.getTokenData(this.pageIndex + 1, this.pageSize, columns, sort, this.filterValue).subscribe({
      next: response => {
        this.length = response.result.value.count;
        this.updateDataSource(response.result.value.tokens);
      },
      error: error => {
        console.error('Failed to get token data', error);
      }
    });
  }

  handlePageEvent(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.fetchTokenData()
  }

  handleSortEvent() {
    this.fetchTokenData()
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim().toLowerCase();
    this.pageIndex = 0;
    this.fetchTokenData()
  }

  private updateDataSource(data: any[]) {
    const processedData = data.map((item) => ({
      ...item,
      realms: item.realms && item.realms.length > 0 ? item.realms[0] : ''
    }));
    this.dataSource.set(new MatTableDataSource(processedData));
  }
}
