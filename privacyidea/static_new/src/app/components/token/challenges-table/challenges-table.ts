import { Component, Input, WritableSignal } from '@angular/core';
import {
  FetchDataHandler,
  FetchDataResponse,
  FilterTable,
  ProcessDataSource,
} from '../../universals/filter-table/filter-table.component';
import {
  OnClickTableColumn as ClickableTableColumn,
  SimpleTableColumn,
  TableColumn,
} from '../../../services/table-utils/table-column';
import { KeywordFilter } from '../../../services/keyword_filter';
import { MatTableDataSource } from '@angular/material/table';
import { ChallengeData } from '../../../model/challenge/challenge-data';
import { TokenService } from '../../../services/token/token.service';
import { TokenSelectedContent } from '../token.component';

@Component({
  selector: 'app-challenges-table',
  standalone: true,
  imports: [FilterTable],
  templateUrl: './challenges-table.component.html',
  styleUrl: './challenges-table.component.scss',
})
export class ChallengesTableComponent {
  constructor(private tokenService: TokenService) {}
  @Input({ required: true })
  selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;

  columns: TableColumn<ChallengeData>[] = [
    new SimpleTableColumn({
      key: 'timestamp',
      label: 'Timestamp',
      getItems: (challenge) => {
        return challenge.timestamp instanceof Date
          ? [challenge.timestamp.toISOString()]
          : [];
      },
    }),
    new ClickableTableColumn({
      key: 'serial',
      label: 'Serial',
      getItems: (challenge) =>
        typeof challenge.serial === 'string' ? [challenge.serial] : [],
      onClick: (challenge) => {
        this.tokenSerial.set(challenge.serial);
        this.selectedContent.set('token_details');
      },
    }),
    new SimpleTableColumn({
      key: 'transaction_id',
      label: 'Transaction ID',
      getItems: (challenge) =>
        typeof challenge.transactionId === 'string'
          ? [challenge.transactionId]
          : [],
    }),
    new SimpleTableColumn({
      key: 'expiration',
      label: 'Expiration',
      getItems: (challenge) =>
        challenge.expiration instanceof Date
          ? [challenge.expiration.toISOString()]
          : [],
    }),
    new SimpleTableColumn({
      key: 'otp_received',
      label: 'OTP Received',
      getItems: (challenge) =>
        typeof challenge.otpReceived === 'boolean'
          ? [challenge.otpReceived ? 'Yes' : 'No']
          : [],
    }),
  ];

  basicFilters: KeywordFilter[] = [
    new KeywordFilter({
      key: 'serial',
      label: 'Serial',
    }),
    new KeywordFilter({
      key: 'transaction_id',
      label: 'Transaction ID',
    }),
  ];
  fetchDataHandler: FetchDataHandler = ({
    pageIndex,
    pageSize,
    sortby_sortdir,
    filterValue,
  }) =>
    this.tokenService.getChallenges({
      pageIndex: pageIndex,
      pageSize: pageSize,
      sort: sortby_sortdir,
      filterValue: filterValue,
    });
  processDataSource: ProcessDataSource<ChallengeData> = (
    response: FetchDataResponse,
  ) =>
    new MatTableDataSource(
      ChallengeData.parseList(response.result.value.challenges),
    );
}
