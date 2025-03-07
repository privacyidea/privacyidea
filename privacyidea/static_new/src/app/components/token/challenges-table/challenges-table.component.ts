import { Component, Input, WritableSignal } from '@angular/core';
import { TokenService } from '../../../services/token/token.service';
import { TokenSelectedContent } from '../token.component';

@Component({
  selector: 'app-challenges-table',
  standalone: true,
  imports: [],
  templateUrl: './challenges-table.component.html',
  styleUrl: './challenges-table.component.scss',
})
export class ChallengesTableComponent {
  @Input({ required: true })
  selectedContent!: WritableSignal<TokenSelectedContent>;
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}

  /*
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
  ) => [
    response.result.value.count,
    new MatTableDataSource(
      ChallengeData.parseList(response.result.value.challenges),
    ),
  ];
  */
}
