import { Component, Input, WritableSignal } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { TokenSelectedContent } from '../../token.component';
import { MachineService } from '../../../../services/machine/machine.service';

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [MatTabsModule],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;
  @Input({ required: true })
  selectedContent!: WritableSignal<TokenSelectedContent>;

  constructor(private machineService: MachineService) {}

  selectToken(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
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
      application: 'ssh',
    });

  processDataSource: ProcessDataSource<MachineTokenData> = (
    response: FetchDataResponse,
  ) => [
    response.result.value.count,
    new MatTableDataSource(MachineTokenData.parseList(response.result.value)),
  ];*/
}
