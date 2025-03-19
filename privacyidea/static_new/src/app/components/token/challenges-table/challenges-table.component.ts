import {
  Component,
  effect,
  Input,
  signal,
  ViewChild,
  WritableSignal,
} from '@angular/core';
import { TokenService } from '../../../services/token/token.service';
import { TokenSelectedContent } from '../token.component';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { KeywordFilterComponent } from '../../shared/keyword-filter/keyword-filter.component';
import { NgClass } from '@angular/common';
import { CdkCopyToClipboard } from '@angular/cdk/clipboard';

export const columnsKeyMap = [
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'serial', label: 'Serial' },
  { key: 'transaction_id', label: 'Transaction ID' },
  { key: 'expiration', label: 'Expiration' },
  { key: 'received', label: 'Received' },
];

@Component({
  selector: 'app-challenges-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    KeywordFilterComponent,
    NgClass,
    CdkCopyToClipboard,
  ],
  templateUrl: './challenges-table.component.html',
  styleUrls: ['./challenges-table.component.scss'],
})
export class ChallengesTableComponent {
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input() tokenSerial!: WritableSignal<string>;
  length = signal(0);
  pageSize = signal(10);
  pageIndex = signal(0);
  filterValue = signal('');
  sortby_sortdir = signal<Sort>({
    active: 'timestamp',
    direction: 'asc',
  });
  dataSource = signal(new MatTableDataSource<any>([]));
  clickedKeyword = signal<string>('');
  columnsKeyMap = columnsKeyMap;
  displayedColumns = columnsKeyMap.map((c) => c.key);
  pageSizeOptions = [5, 10, 15];
  apiFilter = this.tokenService.challengesApiFilter;
  advancedApiFilter = this.tokenService.challengesAdvancedApiFilter;
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild('filterInput', { static: true })
  filterInput!: HTMLInputElement;

  constructor(
    private tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
  ) {
    effect(() => {
      this.filterValue();
      this.fetchChallengesData();
    });
  }

  fetchChallengesData = () => {
    this.tokenService
      .getChallenges({
        pageIndex: this.pageIndex() + 1,
        pageSize: this.pageSize(),
        sort: this.sortby_sortdir(),
        filterValue: this.filterValue(),
      })
      .subscribe({
        next: (response) => {
          this.length.set(response.result.value.count);
          const mappedData = response.result.value.challenges.map(
            (challenge: any) => ({
              challenge_id: challenge.id,
              timestamp: challenge.timestamp,
              serial: challenge.serial,
              transaction_id: challenge.transaction_id,
              expiration: challenge.expiration,
              received: challenge.otp_received,
            }),
          );
          this.dataSource.set(new MatTableDataSource(mappedData));
        },
      });
  };

  tokenSelected(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }
}
