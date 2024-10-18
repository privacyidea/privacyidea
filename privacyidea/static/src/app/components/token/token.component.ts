import {Component, inject, signal, ViewChild} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {LiveAnnouncer} from '@angular/cdk/a11y';
import {AuthService} from '../../services/auth/auth.service';
import {Router} from '@angular/router';
import {HttpClient} from '@angular/common/http';
import {NgForOf} from '@angular/common';

const columns = [
  {key: 'serial', label: 'Serial'},
  {key: 'tokentype', label: 'Type'},
  {key: 'active', label: 'Status'},
  {key: 'description', label: 'Description'},
  {key: 'failcount', label: 'Fail Counter'},
  {key: 'rollout_state', label: 'Rollout Status'},
  {key: 'username', label: 'User'},
  {key: 'user_realm', label: 'Realm'},
  {key: 'token_realm', label: 'Token Realm'},
  {key: 'container_serial', label: 'Container'},
];

@Component({
  selector: 'app-token',
  standalone: true,
  imports: [
    MatTableModule, MatFormFieldModule, MatInputModule, MatTableModule, MatPaginatorModule, MatTableModule,
    MatSortModule, NgForOf
  ],
  templateUrl: './token.component.html',
  styleUrl: './token.component.css'
})
export class TokenComponent {
  private _liveAnnouncer = inject(LiveAnnouncer);
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
        console.log('Token data', response.result.value.tokens);
        this.dataSource.set(new MatTableDataSource(response.result.value.tokens));
      }, error: (error: any) => {
        console.error('Failed to get token data', error);
      }
    });
  }

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  announceSortChange(sortState: Sort) {
    if (sortState.direction) {
      this._liveAnnouncer.announce(`Sorted ${sortState.direction}ending`);
    } else {
      this._liveAnnouncer.announce('Sorting cleared');
    }
  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource().filter = filterValue.trim().toLowerCase();
  }
}
