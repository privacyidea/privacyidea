import {
  Component,
  effect,
  ElementRef,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { TokenSelectedContent } from '../../token.component';
import { MachineService } from '../../../../services/machine/machine.service';
import { KeywordFilterComponent } from '../../../shared/keyword-filter/keyword-filter.component';
import {
  MatCell,
  MatCellDef,
  MatTableDataSource,
  MatTableModule,
} from '@angular/material/table';
import { MatFormField, MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { NgClass } from '@angular/common';
import { TableUtilsService } from '../../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Router } from '@angular/router';
import { AuthService } from '../../../../services/auth/auth.service';
import { MatIcon } from '@angular/material/icon';
import { CdkCopyToClipboard } from '@angular/cdk/clipboard';

const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'serviceid', label: 'Service ID' },
  { key: 'ssh_user', label: 'SSH User' },
];

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [
    MatTabsModule,
    KeywordFilterComponent,
    MatCell,
    MatCellDef,
    MatFormField,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatSortModule,
    NgClass,
    MatIcon,
    CdkCopyToClipboard,
  ],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  length = signal(0);
  pageSize = signal(10);
  pageIndex = signal(0);
  filterValue = signal('');
  dataSource = signal(
    new MatTableDataSource(
      Array.from({ length: this.pageSize() }, () => {
        const emptyRow: any = {};
        columnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
    ),
  );
  sortby_sortdir: WritableSignal<Sort> = signal({
    active: 'serial',
    direction: 'asc',
  });
  keywordClick = signal<string>('');

  columnsKeyMap = columnsKeyMap;
  displayedColumns: string[] = columnsKeyMap.map((column) => column.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.machineService.sshApiFilter;
  advancedApiFilter = this.machineService.sshAdvancedApiFilter;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('input') inputElement!: ElementRef<HTMLInputElement>;

  constructor(
    private router: Router,
    private authService: AuthService,
    private machineService: MachineService,
    protected tableUtilsService: TableUtilsService,
    private notificationService: NotificationService,
  ) {
    effect(() => {
      const clickedKeyword = this.keywordClick();
      if (clickedKeyword) {
        this.toggleKeywordInFilter(
          clickedKeyword,
          this.inputElement.nativeElement,
        );
        this.keywordClick.set('');
      }
    });

    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then((r) => {
        console.warn('Redirected to login page.', r);
        this.notificationService.openSnackBar('Redirected to login page.');
      });
    } else {
      this.fetchApplicationData();
    }
  }

  toggleKeywordInFilter(
    filterKeyword: string,
    inputElement: HTMLInputElement,
  ): void {
    if (filterKeyword === 'machineid & resolver') {
      inputElement.value = this.tableUtilsService.toggleKeywordInFilter(
        inputElement.value.trim(),
        'machineid',
      );
      this.tableUtilsService.handleFilterInput(
        {
          target: inputElement,
        } as unknown as KeyboardEvent,
        this.pageIndex,
        this.filterValue,
        this.fetchApplicationData,
      );
      inputElement.value = this.tableUtilsService.toggleKeywordInFilter(
        inputElement.value.trim(),
        'resolver',
      );
      this.tableUtilsService.handleFilterInput(
        {
          target: inputElement,
        } as unknown as KeyboardEvent,
        this.pageIndex,
        this.filterValue,
        this.fetchApplicationData,
      );
      inputElement.focus();
    } else {
      inputElement.value = this.tableUtilsService.toggleKeywordInFilter(
        inputElement.value.trim(),
        filterKeyword,
      );
    }
    this.tableUtilsService.handleFilterInput(
      {
        target: inputElement,
      } as unknown as KeyboardEvent,
      this.pageIndex,
      this.filterValue,
      this.fetchApplicationData,
    );
    inputElement.focus();
  }

  selectToken(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }

  tokenSelected(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  fetchApplicationData = () => {
    this.machineService
      .getTokenMachineData(
        this.pageSize(),
        this.filterValue(),
        'ssh',
        'serial',
        'asc',
        this.pageIndex(),
      )
      .subscribe({
        next: (response) => {
          this.length.set(response.result.value.length);
          let mappedData = response.result.value.map((value: any) => {
            return {
              serial: value.serial,
              serviceid: value.options.service_id,
              ssh_user: value.options.user,
            };
          });
          this.dataSource.set(new MatTableDataSource(mappedData));
        },
        error: (error) => {
          console.error('Failed to get token data.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to get token data. ' + message,
          );
        },
      });
  };
}
