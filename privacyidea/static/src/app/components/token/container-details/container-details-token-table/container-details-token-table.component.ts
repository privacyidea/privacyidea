import {Component, Input, ViewChild, WritableSignal} from '@angular/core';
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableModule
} from '@angular/material/table';
import {MatFormField, MatLabel} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatPaginator} from '@angular/material/paginator';
import {MatSort, MatSortHeader, MatSortModule} from '@angular/material/sort';
import {Router} from '@angular/router';
import {AuthService} from '../../../../services/auth/auth.service';
import {TokenService} from '../../../../services/token/token.service';
import {TableUtilsService} from '../../../../services/table-utils/table-utils.service';
import {NgClass} from '@angular/common';

const columnsKeyMap = [
  {key: 'serial', label: 'Serial'},
  {key: 'tokentype', label: 'Type'},
  {key: 'active', label: 'Active'},
  {key: 'username', label: 'User'},
];

@Component({
  selector: 'app-container-details-token-table',
  imports: [
    MatCell,
    MatFormField,
    MatHeaderCell,
    MatHeaderRow,
    MatInput,
    MatLabel,
    MatPaginator,
    MatRow,
    MatSort,
    MatSortHeader,
    MatTable,
    NgClass,
    MatTableModule,
    MatSortModule,
  ],
  templateUrl: './container-details-token-table.component.html',
  styleUrl: './container-details-token-table.component.scss'
})
export class ContainerDetailsTokenTableComponent {
  displayedColumns: string[] = columnsKeyMap.map(column => column.key);
  pageSize = 10;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';
  @Input() dataSource!: WritableSignal<any>;
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  @Input() serial!: WritableSignal<string>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  protected readonly columnsKeyMap = columnsKeyMap;

  constructor(private router: Router,
              private authService: AuthService,
              protected tokenService: TokenService,
              protected tableUtilsService: TableUtilsService) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then(r => console.warn('Redirected to login page', r));
    }
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.dataSource().filter = this.filterValue.trim().toLowerCase();
  }

  tokenSelected(serial: string) {
    this.serial.set(serial);
    this.tokenIsSelected.set(true)
  }
}
