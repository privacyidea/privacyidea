import {
  Component,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import {
  MatPaginator,
  MatPaginatorModule,
  PageEvent,
} from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { AuthService } from '../../../services/auth/auth.service';
import { Router } from '@angular/router';
import { NgClass } from '@angular/common';
import { TokenService } from '../../../services/token/token.service';
import { MatIcon } from '@angular/material/icon';
import { MatFabButton } from '@angular/material/button';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { CdkCopyToClipboard } from '@angular/cdk/clipboard';

const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'tokentype', label: 'Type' },
  { key: 'active', label: 'Active' },
  { key: 'description', label: 'Description' },
  { key: 'failcount', label: 'Fail Counter' },
  { key: 'rollout_state', label: 'Rollout State' },
  { key: 'username', label: 'User' },
  { key: 'user_realm', label: 'User Realm' },
  { key: 'realms', label: 'Token Realm' },
  { key: 'container_serial', label: 'Container' },
];

@Component({
  selector: 'app-token-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    MatPaginatorModule,
    MatTableModule,
    MatSortModule,
    NgClass,
    MatIcon,
    MatFabButton,
    CdkCopyToClipboard,
  ],
  templateUrl: './token-table.component.html',
  styleUrl: './token-table.component.scss',
})
export class TokenTableComponent {
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  length = 0;
  pageSize = 10;
  pageIndex = 0;
  pageSizeOptions = [5, 10, 15];
  filterValue = '';
  apiFilter = this.tokenService.apiFilter;
  advancedApiFilter = this.tokenService.advancedApiFilter;
  sortby_sortdir:
    | { active: string; direction: 'asc' | 'desc' | '' }
    | undefined;
  dataSource = signal(
    new MatTableDataSource(
      Array.from({ length: this.pageSize }, () => {
        const emptyRow: any = {};
        columnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
    ),
  );
  showAdvancedFilter = signal(false);
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() containerSerial!: WritableSignal<string>;
  @Input() isProgrammaticChange!: WritableSignal<boolean>;
  @Input() selectedContent!: WritableSignal<string>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  protected readonly columnsKeyMap = columnsKeyMap;

  constructor(
    private router: Router,
    private authService: AuthService,
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    private notificationService: NotificationService,
  ) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then((r) => {
        console.warn('Redirected to login page.', r);
        this.notificationService.openSnackBar('Redirected to login page.');
      });
    } else {
      this.fetchTokenData();
    }
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.paginator;
    this.dataSource().sort = this.sort;
  }

  handlePageEvent(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.fetchTokenData();
  }

  handleSortEvent() {
    this.sortby_sortdir = this.sort
      ? {
          active: this.sort.active,
          direction: this.sort.direction,
        }
      : undefined;
    this.pageIndex = 0;
    this.fetchTokenData();
  }

  handleFilterInput(event: Event) {
    this.filterValue = (event.target as HTMLInputElement).value.trim();
    this.pageIndex = 0;
    this.fetchTokenData();
  }

  toggleKeywordInFilter(
    filterKeyword: string,
    inputElement: HTMLInputElement,
  ): void {
    if (filterKeyword === 'active') {
      inputElement.value = this.tableUtilsService.toggleActiveInFilter(
        inputElement.value,
      );
      this.handleFilterInput({
        target: inputElement,
      } as unknown as KeyboardEvent);
      inputElement.focus();
      return;
    }

    if (filterKeyword === 'infokey & infovalue') {
      inputElement.value = this.tableUtilsService.toggleKeywordInFilter(
        inputElement.value.trim(),
        'infokey',
      );
      this.handleFilterInput({
        target: inputElement,
      } as unknown as KeyboardEvent);
      inputElement.value = this.tableUtilsService.toggleKeywordInFilter(
        inputElement.value.trim(),
        'infovalue',
      );
      this.handleFilterInput({
        target: inputElement,
      } as unknown as KeyboardEvent);
      inputElement.focus();
    } else {
      inputElement.value = this.tableUtilsService.toggleKeywordInFilter(
        inputElement.value.trim(),
        filterKeyword,
      );
      this.handleFilterInput({
        target: inputElement,
      } as unknown as KeyboardEvent);
      inputElement.focus();
    }
  }

  toggleActive(element: any): void {
    this.tokenService.toggleActive(element.serial, element.active).subscribe({
      next: () => {
        this.fetchTokenData();
      },
      error: (error) => {
        console.error('Failed to toggle active.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to toggle active. ' + message,
        );
      },
    });
  }

  resetFailCount(element: any): void {
    this.tokenService.resetFailCount(element.serial).subscribe({
      next: () => {
        this.fetchTokenData();
      },
      error: (error) => {
        console.error('Failed to reset fail counter.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to reset fail counter. ' + message,
        );
      },
    });
  }

  handleColumnClick(columnKey: string, element: any): void {
    if (element.revoked || element.locked) {
      return;
    }
    if (columnKey === 'active') {
      this.toggleActive(element);
    } else if (columnKey === 'failcount') {
      this.resetFailCount(element);
    }
  }

  tokenSelected(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  containerSelected(containerSerial: string) {
    this.isProgrammaticChange.set(true);
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }

  private fetchTokenData() {
    this.tokenService
      .getTokenData(
        this.pageIndex + 1,
        this.pageSize,
        this.sortby_sortdir,
        this.filterValue,
      )
      .subscribe({
        next: (response) => {
          this.length = response.result.value.count;
          this.dataSource.set(
            new MatTableDataSource(response.result.value.tokens),
          );
        },
        error: (error) => {
          console.error('Failed to get token data.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to get token data. ' + message,
          );
        },
      });
  }
}
