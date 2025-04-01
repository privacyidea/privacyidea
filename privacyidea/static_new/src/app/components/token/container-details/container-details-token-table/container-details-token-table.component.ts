import { Component, Input, ViewChild, WritableSignal } from '@angular/core';
import {
  MatCell,
  MatHeaderCell,
  MatHeaderRow,
  MatRow,
  MatTable,
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
import { ContainerService } from '../../../../services/container/container.service';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmationDialogComponent } from '../../../shared/confirmation-dialog/confirmation-dialog.component';
import { TokenSelectedContent } from '../../token.component';
import { CopyButtonComponent } from '../../../shared/copy-button/copy-button.component';

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
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  protected readonly columnsKeyMap = columnsKeyMap;

  constructor(
    private containerService: ContainerService,
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    protected overflowService: OverflowService,
    private dialog: MatDialog,
  ) {}

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
    this.selectedContent.set('token_details');
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
                  this.refreshContainerDetails.set(true);
                },
              });
          }
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
    });
  }

  toggleAll(action: 'activate' | 'deactivate') {
    this.containerService.toggleAll(this.containerSerial(), action).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
    });
  }

  removeAll() {
    const serial_list = this.dataSource()
      .data.map((token: any) => token.serial)
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
                this.refreshContainerDetails.set(true);
              },
            });
          }
        },
      });
  }

  deleteAllTokens() {
    const serialList = this.dataSource()
      .data.map((token: any) => token.serial)
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
                  this.refreshContainerDetails.set(true);
                },
              });
          }
        },
      });
  }
}
