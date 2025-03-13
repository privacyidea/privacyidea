import {
  Component,
  effect,
  Input,
  signal,
  WritableSignal,
} from '@angular/core';
import { TokenApplicationsSsh } from './token-applications-ssh/token-applications-ssh';
import { TokenApplicationsOffline } from './token-applications-offline/token-applications-offline';
import { MatSelectModule } from '@angular/material/select';
import { TokenSelectedContent } from '../token.component';
import { Sort } from '@angular/material/sort';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { MatTableDataSource } from '@angular/material/table';
import { MachineService } from '../../../services/machine/machine.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { AuthService } from '../../../services/auth/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-token-applications',
  standalone: true,
  imports: [TokenApplicationsSsh, TokenApplicationsOffline, MatSelectModule],
  templateUrl: './token-applications.html',
  styleUrls: ['./token-applications.scss'],
})
export class TokenApplications {
  sshColumnsKeyMap = TokenApplicationsSsh.columnsKeyMap;
  offlineColumnsKeyMap = TokenApplicationsOffline.columnsKeyMap;
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  selectedApplicationType = signal('ssh');
  length = signal(0);
  pageSize = signal(10);
  pageIndex = signal(0);
  filterValue = signal('');
  sortby_sortdir: WritableSignal<Sort> = signal({
    active: 'serial',
    direction: 'asc',
  });
  sshDataSource = signal(
    new MatTableDataSource(
      Array.from({ length: this.pageSize() }, () => {
        const emptyRow: any = {};
        this.sshColumnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
    ),
  );
  offlineDataSource = signal(
    new MatTableDataSource(
      Array.from({ length: this.pageSize() }, () => {
        const emptyRow: any = {};
        this.offlineColumnsKeyMap.forEach((column) => {
          emptyRow[column.key] = '';
        });
        return emptyRow;
      }),
    ),
  );

  constructor(
    private tableUtilsService: TableUtilsService,
    private machineService: MachineService,
    private notificationService: NotificationService,
    private authService: AuthService,
    private router: Router,
  ) {
    if (!this.authService.isAuthenticatedUser()) {
      this.router.navigate(['']).then((r) => {
        console.warn('Redirected to login page.', r);
        this.notificationService.openSnackBar('Redirected to login page.');
      });
    } else {
      this.fetchApplicationSshData();
      this.fetchApplicationOfflineData();
    }

    effect(() => {
      if (this.selectedApplicationType()) {
        this.filterValue.set('');
      }
    });
  }

  tokenSelected(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  toggleKeywordInFilter(
    filterKeyword: string,
    inputElement: HTMLInputElement,
    application: string,
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
        application === 'ssh'
          ? this.fetchApplicationSshData
          : this.fetchApplicationOfflineData,
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
        application === 'ssh'
          ? this.fetchApplicationSshData
          : this.fetchApplicationOfflineData,
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
      application === 'ssh'
        ? this.fetchApplicationSshData
        : this.fetchApplicationOfflineData,
    );
    inputElement.focus();
  }

  fetchApplicationSshData = () => {
    this.machineService
      .getTokenMachineData(
        this.pageSize(),
        this.filterValue(),
        'ssh',
        this.sortby_sortdir().active,
        this.sortby_sortdir().direction,
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
          this.sshDataSource.set(new MatTableDataSource(mappedData));
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

  fetchApplicationOfflineData = () => {
    this.machineService
      .getTokenMachineData(
        this.pageSize(),
        this.filterValue(),
        'offline',
        this.sortby_sortdir().active,
        this.sortby_sortdir().direction,
        this.pageIndex(),
      )
      .subscribe({
        next: (response) => {
          this.length.set(response.result.value.length);
          const mappedData = response.result.value.map((value: any) => ({
            serial: value.serial,
            count: value.options.count,
            rounds: value.options.rounds,
          }));
          this.offlineDataSource.set(new MatTableDataSource(mappedData));
        },
        error: (error) => {
          const message = error.error?.result?.error?.message || ``;
          this.notificationService.openSnackBar(
            'Failed to get offline token data. ' + message,
          );
        },
      });
  };
}
