import {Component, signal, ViewChild} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule} from '@angular/material/sort';
import {AuthService} from '../../../services/auth/auth.service';
import {Router} from '@angular/router';
import {NgClass, NgStyle} from '@angular/common';
import {MatCard, MatCardContent} from '@angular/material/card';
import {TokenService} from '../../../services/token/token.service';
import {MatIcon} from '@angular/material/icon';
import {MatFabButton} from '@angular/material/button';
import {TableUtilsService} from '../../../services/table-utils/table-utils.service';
import {TokenDetailsComponent} from '../token-details/token-details.component';

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
    MatSortModule, MatCard, MatCardContent, NgClass, MatIcon, MatFabButton, NgStyle, TokenDetailsComponent
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
  apiFilter = this.tokenService.apiFilter;
  sortby_sortdir: { active: string; direction: "asc" | "desc" | "" } | undefined;
  serial = '';

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  protected readonly columns = columns;
  protected tokenIsSelected = signal(false);

  constructor(private router: Router,
              private authService: AuthService,
              protected tokenService: TokenService,
              protected tableUtilsService: TableUtilsService) {
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

  private fetchTokenData() {
    this.tokenService.getTokenData(
      this.pageIndex + 1, this.pageSize, columns, this.sortby_sortdir, this.filterValue).subscribe({
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
    this.sortby_sortdir = this.sort ? {active: this.sort.active, direction: this.sort.direction} : undefined;
    this.pageIndex = 0;
    this.fetchTokenData()
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.pageIndex = 0;
    this.fetchTokenData()
  }

  toggleKeywordInFilter(keyword: string, inputElement: HTMLInputElement): void {
    inputElement.value = this.tableUtilsService.toggleKeywordInFilter(inputElement.value.trim(), keyword);
    this.handleFilterInput({target: inputElement} as unknown as KeyboardEvent);
    inputElement.focus();
  }

  toggleActive(element: any): void {
    this.tokenService.toggleActive(element).subscribe({
      next: () => {
        this.fetchTokenData();
      },
      error: error => {
        console.error('Failed to toggle active', error);
      }
    });
  }

  resetFailCount(element: any): void {
    this.tokenService.resetFailCount(element).subscribe({
      next: () => {
        this.fetchTokenData();
      },
      error: error => {
        console.error('Failed to reset fail counter', error);
      }
    });
  }

  private updateDataSource(data: any[]) {
    const processedData = data.map((item) => ({
      ...item,
      realms: item.realms && item.realms.length > 0 ? item.realms[0] : ''
    }));
    this.dataSource.set(new MatTableDataSource(processedData));
  }

  tokenSelected(serial: string) {
    this.tokenIsSelected.set(true)
    this.serial = serial;
  }
}
