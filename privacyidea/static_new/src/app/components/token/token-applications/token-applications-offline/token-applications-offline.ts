import { Component, Input, WritableSignal } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MachineService } from '../../../../services/machine/machine.service';
import { TokenSelectedContent } from '../../token.component';

@Component({
  selector: 'app-token-applications-offline',
  standalone: true,
  imports: [MatTabsModule],
  templateUrl: './token-applications-offline.html',
  styleUrls: ['./token-applications-offline.scss'],
})
export class TokenApplicationsOffline {
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() selectedContent!: WritableSignal<TokenSelectedContent>;

  constructor(private machineService: MachineService) {}

  selectToken(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  /*
  fetchDataHandler: FetchDataHandler = ({
    pageIndex,
    pageSize,
    sortby_sortdir,
    filterValue: currentFilter,
  }) =>
    this.machineService.getToken({
      sortby: sortby_sortdir?.active,
      sortdir: sortby_sortdir?.direction,
      page: pageIndex,
      pageSize: pageSize,
      currentFilter: currentFilter,
      application: 'offline',
    });

  processDataSource: ProcessDataSource<MachineTokenData> = (
    response: FetchDataResponse,
  ) => [
    response.result.value.count,
    new MatTableDataSource(MachineTokenData.parseList(response.result.value)),
  ];
  */
}
