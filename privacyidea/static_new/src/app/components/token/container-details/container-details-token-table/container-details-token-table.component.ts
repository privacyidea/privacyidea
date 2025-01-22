import {Component, Input, ViewChild, WritableSignal} from '@angular/core';
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableModule,
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
import {NotificationService} from '../../../../services/notification/notification.service';
import {MatDialog} from '@angular/material/dialog';
import {
  ConfirmationDialogComponent
} from '../../token-card/container-tab/confirmation-dialog/confirmation-dialog.component';

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
  styleUrl: './container-details-token-table.component.scss',
})
export class ContainerDetailsTokenTableComponent {
  displayedColumns: string[] = [
    ...columnsKeyMap.map((column) => column.key),
    'remove',
  ];
  pageSize = 10;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';
  @Input() dataSource!: WritableSignal<any>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() refreshContainerDetails!: WritableSignal<boolean>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  @Input() selectedContent!: WritableSignal<string>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  protected readonly columnsKeyMap = columnsKeyMap;

  constructor(
    private router: Router,
    private authService: AuthService,
    private containerService: ContainerService,
    private notificationService: NotificationService,
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    protected overflowService: OverflowService,
    private dialog: MatDialog
  ) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then((r) => {
        console.warn('Redirected to login page.', r);
        this.notificationService.openSnackBar('Redirected to login page.');
      });
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

  tokenSelected(tokenSerial: string) {
    this.isProgrammaticChange.set(true);
    this.tokenSerial.set(tokenSerial);
    this.selectedContent.set('token_details')
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    this.containerService
      .removeTokenFromContainer(containerSerial, tokenSerial)
      .subscribe({
        next: () => {
          this.refreshContainerDetails.set(true);
        },
        error: (error) => {
          console.error('Failed to remove token from container.', error);
          this.notificationService.openSnackBar(
            'Failed to remove token from container.'
          );
        },
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
      error: (error) => {
        console.error('Failed to toggle active.', error);
        this.notificationService.openSnackBar('Failed to toggle active.');
      },
    });
  }

  toggleAll(action: string) {
    this.containerService.toggleAll(this.containerSerial(), action).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
      error: (error) => {
        console.error('Failed to toggle all.', error);
        this.notificationService.openSnackBar('Failed to toggle all.');
      },
    });
  }

  deleteAllTokens() {
    const serial_list = this.dataSource()
      .data.map((token: any) => token.serial)
      .join(',');
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: serial_list.split(','),
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService
              .deleteAllTokens(this.containerSerial(), serial_list)
              .subscribe({
                next: () => {
                  this.refreshContainerDetails.set(true);
                },
                error: (error) => {
                  console.error('Failed to delete all tokens.', error);
                  this.notificationService.openSnackBar(
                    'Failed to delete all tokens.'
                  );
                },
              });
          }
        },
      });
  }
}
