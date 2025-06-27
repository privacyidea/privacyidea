import {
  Component,
  computed,
  effect,
  Input,
  linkedSignal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort, MatSortHeader, MatSortModule } from '@angular/material/sort';
import { TokenService } from '../../../../services/token/token.service';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { NgClass } from '@angular/common';
import { MatIcon } from '@angular/material/icon';
import { MatButton, MatIconButton } from '@angular/material/button';
import {
  ContainerDetailToken,
  ContainerService,
} from '../../../../services/container/container.service';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ContentService } from '../../../../services/content/content.service';
import { AuthService } from '../../../../services/auth/auth.service';
import { UserAssignmentDialogComponent } from '../user-assignment-dialog/user-assignment-dialog.component';

const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'tokentype', label: 'Type' },
  { key: 'active', label: 'Active' },
  { key: 'username', label: 'User' },
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
    CopyButtonComponent,
    ReactiveFormsModule,
    FormsModule,
  ],
  templateUrl: './container-details-token-table.component.html',
  styleUrl: './container-details-token-table.component.scss',
})
export class ContainerDetailsTokenTableComponent {
  protected readonly columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = [
    ...columnsKeyMap.map((column) => column.key),
    'remove',
  ];
  pageSize = 10;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';
  @Input() containerTokenData!: WritableSignal<
    MatTableDataSource<ContainerDetailToken, MatPaginator>
  >;
  dataSource = new MatTableDataSource<ContainerDetailToken>([]);
  containerSerial = this.containerService.containerSerial;
  assignedUser: WritableSignal<{
    user_realm: string;
    user_name: string;
    user_resolver: string;
    user_id: string;
  }> = linkedSignal({
    source: () => this.containerService.containerDetail(),
    computation: (source, previous) =>
      source.containers[0]?.users[0] ??
      previous?.value ?? {
        user_realm: '',
        user_name: '',
        user_resolver: '',
        user_id: '',
      },
  });
  tokenSerial = this.tokenService.tokenSerial;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;
  selectedContent = this.contentService.selectedContent;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  isAssignableToAllToken = computed<boolean>(() => {
    const assignedUser = this.assignedUser();
    if (assignedUser.user_name === '') {
      return false;
    }
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username === '');
  });

  isUnassignableFromAllToken = computed<boolean>(() => {
    const tokens = this.containerTokenData().data;
    return tokens.some((token) => token.username !== '');
  });

  constructor(
    protected containerService: ContainerService,
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    protected overflowService: OverflowService,
    private dialog: MatDialog,
    protected contentService: ContentService,
    protected authService: AuthService,
  ) {
    effect(() => {
      const containerDetails = this.containerTokenData();
      if (containerDetails) {
        this.dataSource.data = containerDetails.data ?? [];
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.dataSource.filter = this.filterValue.trim().toLowerCase();
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string) {
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: [tokenSerial],
          title: 'Remove Token',
          type: 'token',
          action: 'remove',
          numberOfTokens: [tokenSerial].length,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService
              .removeTokenFromContainer(containerSerial, tokenSerial)
              .subscribe({
                next: () => {
                  this.containerService.containerDetailResource.reload();
                },
              });
          }
        },
      });
  }

  handleColumnClick(columnKey: string, token: ContainerDetailToken) {
    if (columnKey === 'active') {
      this.toggleActive(token);
    }
  }

  unassignFromAllToken() {
    const tokenToUnassign = this.containerTokenData().data.filter(
      (token) => token.username !== '',
    );
    if (tokenToUnassign.length === 0) {
      return;
    }
    const tokenSerials = tokenToUnassign.map((token) => token.serial);
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          type: 'token',
          serial_list: tokenSerials,
          title: 'Unassign User from All Tokens',
          action: 'unassign',
          numberOfTokens: tokenSerials.length,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.tokenService.unassignUserFromAll(tokenSerials).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              },
              error: (error) => {
                console.error('Error unassigning user from token:', error);
              },
            });
          }
        },
      });
  }

  assignToAllToken() {
    var username = this.assignedUser().user_name;
    var realm = this.assignedUser().user_realm;
    if (username === '' || realm === '') {
      this.dialog.open(ConfirmationDialogComponent, {
        data: {
          title: 'No User Assigned',
          message: 'Please assign a user to the Container first.',
        },
      });
      return;
    }

    var tokensToAssign = this.containerTokenData().data.filter((token) => {
      return token.username !== username;
    });
    if (tokensToAssign.length === 0) {
      return;
    }
    var tokensAssignedToOtherUser = tokensToAssign.filter(
      (token) => token.username !== '',
    );

    this.dialog
      .open(UserAssignmentDialogComponent)
      .afterClosed()
      .subscribe((pin: string) => {
        if (typeof pin !== 'string') {
          return;
        }
        const tokenSerialsAssignedToOtherUser = tokensAssignedToOtherUser.map(
          (token) => token.serial,
        );
        this.tokenService
          .unassignUserFromAll(tokenSerialsAssignedToOtherUser)
          .subscribe({
            next: () => {
              const tokenSerialsToAssign = tokensToAssign.map(
                (token) => token.serial,
              );
              this.tokenService
                .assignUserToAll({
                  tokenSerials: tokenSerialsToAssign,
                  username: username,
                  realm: realm,
                  pin: pin,
                })
                .subscribe({
                  next: () => {
                    this.containerService.containerDetailResource.reload();
                  },
                  error: (error) => {
                    console.error('Error assigning user to all tokens:', error);
                  },
                });
            },
            error: (error) => {
              console.error('Error unassigning user from all tokens:', error);
            },
          });
      });
  }

  toggleActive(token: ContainerDetailToken): void {
    this.tokenService.toggleActive(token.serial, token.active).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      },
    });
  }

  toggleAll(action: 'activate' | 'deactivate') {
    this.containerService.toggleAll(action).subscribe({
      next: () => {
        this.containerService.containerDetailResource.reload();
      },
    });
  }

  removeAll() {
    const serial_list = this.containerTokenData()
      .data.map((token) => token.serial)
      .join(',');
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: serial_list.split(','),
          title: 'Remove Token',
          type: 'token',
          action: 'remove',
          numberOfTokens: serial_list.split(',').length,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService.removeAll(this.containerSerial()).subscribe({
              next: () => {
                this.containerService.containerDetailResource.reload();
              },
            });
          }
        },
      });
  }

  deleteAllTokens() {
    const serialList = this.containerTokenData()
      .data.map((token) => token.serial)
      .join(',');
    this.dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serial_list: serialList.split(','),
          title: 'Delete All Tokens',
          type: 'token',
          action: 'delete',
          numberOfTokens: serialList.split(',').length,
        },
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.containerService
              .deleteAllTokens({
                containerSerial: this.containerSerial(),
                serialList: serialList,
              })
              .subscribe({
                next: () => {
                  this.containerService.containerDetailResource.reload();
                },
              });
          }
        },
      });
  }
}
