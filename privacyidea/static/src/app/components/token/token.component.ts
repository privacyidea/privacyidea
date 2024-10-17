import {Component, inject, ViewChild} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatPaginator, MatPaginatorModule} from '@angular/material/paginator';
import {MatInputModule} from '@angular/material/input';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {LiveAnnouncer} from '@angular/cdk/a11y';
import {AuthService} from '../../services/auth/auth.service';
import {Router} from '@angular/router';
import {HttpClient} from '@angular/common/http';

export interface TokenData {
  type: string;
  serial: string;
  active: string;
  description: string;
  fail_counter: number;
  rollout_status: string;
  user: string;
  realm: string;
  token_realm: string;
  container: string;
}

@Component({
  selector: 'app-token',
  standalone: true,
  imports: [
    MatTableModule, MatFormFieldModule, MatInputModule, MatTableModule, MatPaginatorModule, MatTableModule, MatSortModule
  ],
  templateUrl: './token.component.html',
  styleUrl: './token.component.css'
})
export class TokenComponent {
  private _liveAnnouncer = inject(LiveAnnouncer);
  private headerDict = {headers: {'PI-Authorization': localStorage.getItem('bearer_token')}}
  dataSource = new MatTableDataSource<TokenData>();
  displayedColumns: string[] = ['serial', 'tokentype', 'active', 'description', 'failcount', 'rollout_state', 'username',
    'realm', 'token_realm', 'container_serial'];

  constructor(private authService: AuthService, private router: Router, private http: HttpClient) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.log('Redirected to login page', r));
    }

    // @ts-ignore
    this.http.get('http://127.0.0.1:5000/token', this.headerDict).subscribe({
      next: (response: any) => {
        console.log('Token data', response.result.value.tokens);
        this.dataSource = new MatTableDataSource(response.result.value.tokens);
      }, error: (error: any) => {
        console.error('Failed to get token data', error);
      }
    });
  }

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
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
    this.dataSource.filter = filterValue.trim().toLowerCase();
  }
}
