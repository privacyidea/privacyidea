import {Component, signal, ViewChild} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {AuthService} from '../../../services/auth/auth.service';
import {Router} from '@angular/router';
import {HttpClient} from '@angular/common/http';
import {NgClass, NgForOf, NgIf} from '@angular/common';
import {MatCard, MatCardContent} from '@angular/material/card';

const columns = [
  {key: 'serial', label: 'Serial'},
  {key: 'tokentype', label: 'Type'},
  {key: 'active', label: 'Active'},
  {key: 'description', label: 'Description'},
  {key: 'failcount', label: 'Fail Counter'},
  {key: 'rollout_state', label: 'Rollout Status'},
  {key: 'username', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
  {key: 'token_realm', label: 'Token Realm'},
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
  private headerDict = {headers: {'PI-Authorization': localStorage.getItem('bearer_token') || ''}}
  dataSource = signal(new MatTableDataSource());
  displayedColumns: string[] = columns.map(column => column.key);
  columnDefinitions = columns;

  constructor(private authService: AuthService, private router: Router, private http: HttpClient) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.log('Redirected to login page', r));
    }

    this.http.get('http://127.0.0.1:5000/token', this.headerDict).subscribe({
      next: (response: any) => {
        console.log('Token data', response.result.value.tokens); // TODO map values correctly and remove this line
        this.dataSource.set(new MatTableDataSource(response.result.value.tokens));
      }, error: (error: any) => {
        console.error('Failed to get token data', error);
      }
    });
  }

  @ViewChild(MatPaginator) paginator: MatPaginator | null = null;
  @ViewChild(MatSort) sort: MatSort | null = null;

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource().filter = filterValue.trim().toLowerCase();
  }

  sortData(sort: Sort) {
    if (!sort.active || sort.direction === '') {
      this.dataSource().data = this.dataSource().data;
      return;
    }

    function compare(a: string | number, b: string | number, isAsc: boolean) {
      return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
    }

    this.dataSource().data = this.dataSource().data.slice().sort((a: any, b: any) => {
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
  }

  protected readonly columns = columns;
}
