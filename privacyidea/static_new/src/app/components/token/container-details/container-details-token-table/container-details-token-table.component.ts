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
import {MatIcon} from '@angular/material/icon';
import {MatButton, MatIconButton} from '@angular/material/button';
import {ContainerService} from '../../../../services/container/container.service';
import {OverflowService} from '../../../../services/overflow/overflow.service';

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
    MatIcon,
    MatIconButton,
    MatButton,
  ],
  templateUrl: './container-details-token-table.component.html',
  styleUrl: './container-details-token-table.component.scss'
})
export class ContainerDetailsTokenTableComponent {
  displayedColumns: string[] = [
    ...columnsKeyMap.map(column => column.key),
    'remove'
  ];
  pageSize = 10;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';
  @Input() dataSource!: WritableSignal<any>;
  @Input() tokenIsSelected!: WritableSignal<boolean>;
  @Input() containerIsSelected!: WritableSignal<boolean>;
  @Input() container_serial!: WritableSignal<string>;
  @Input() token_serial!: WritableSignal<string>;
  @Input() selectedTabIndex!: WritableSignal<number>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  protected readonly columnsKeyMap = columnsKeyMap;

  constructor(private router: Router,
              private authService: AuthService,
              private containerService: ContainerService,
              protected tokenService: TokenService,
              protected tableUtilsService: TableUtilsService,
              protected overflowService: OverflowService) {
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

  tokenSelected(token_serial: string) {
    this.token_serial.set(token_serial);
    this.containerIsSelected.set(false);
    this.isProgrammaticChange.set(true);
    this.selectedTabIndex.set(0);
    this.tokenIsSelected.set(true);
  }

  removeTokenFromContainer(container_serial: string, token_serial: string) {
    this.containerService.removeTokenFromContainer(container_serial, token_serial).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
      error: error => {
        console.error('Failed to remove token from container', error);
      }
    });
  }

  handleColumnClick(columnKey: string, element: any) {
    if (columnKey === 'active') {
      this.toggleActive(element);
    }
  }

  toggleActive(element: any): void {
    this.tokenService.toggleActive(element.serial, element.active).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
      error: error => {
        console.error('Failed to toggle active', error);
      }
    });
  }

  toggleAll(action: string) {
    this.containerService.toggleAll(this.container_serial(), action).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
      error: error => {
        console.error('Failed to activate all', error);
      }
    });
  }
}
