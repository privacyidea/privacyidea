import { Component, Input, WritableSignal } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import {
  FetchDataHandler,
  FilterTable,
  SortDir,
  ProcessDataSource,
} from '../../../universals/filter-table/filter-table.component';
import { MachineService } from '../../../../services/machine/machine.service';
import { KeywordFilter } from '../../../../services/keyword_filter';
import {
  OnClickTableColumn,
  SimpleTableColumn,
  TableColumn,
} from '../../../../services/table-utils/table-column';
import { MatTableDataSource } from '@angular/material/table';
import { MachineTokenData } from '../../../../model/machine/machine-token-data';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [MatTabsModule, FilterTable],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;
  @Input({ required: true }) selectedContent!: WritableSignal<string>;

  basicFilters: KeywordFilter[] = [
    new KeywordFilter({
      key: 'serial',
      label: 'Serial',
    }),
    new KeywordFilter({
      key: 'hostname',
      label: 'Hostname',
    }),
    new KeywordFilter({
      key: 'machineid',
      label: 'Machine ID',
    }),
    new KeywordFilter({
      key: 'resolver',
      label: 'Resolver',
    }),
    new KeywordFilter({
      key: 'service_id',
      label: 'Service ID',
    }),
    new KeywordFilter({
      key: 'user',
      label: 'User',
    }),
  ];

  columns: TableColumn<MachineTokenData>[] = [
    // new SimpleTableColumn({
    //   key: 'application',
    //   label: 'Application',
    //   getItems: (sshToken) =>
    //     sshToken.application ? [sshToken.application] : [],
    // }),
    new SimpleTableColumn({
      key: 'id',
      label: 'ID',
      getItems: (sshToken) => (sshToken.id ? [sshToken.id.toString()] : []),
    }),
    new SimpleTableColumn({
      key: 'machine_id',
      label: 'Machine ID',
      getItems: (sshToken) =>
        sshToken.machine_id ? [sshToken.machine_id] : [],
    }),
    new SimpleTableColumn({
      key: 'options',
      label: 'Options',
      getItems: (sshToken) =>
        sshToken.options ? this.getObjectStrings(sshToken.options) : [],
    }),
    new SimpleTableColumn({
      key: 'resolver',
      label: 'Resolver',
      getItems: (sshToken) => (sshToken.resolver ? [sshToken.resolver] : []),
    }),
    new OnClickTableColumn({
      key: 'serial',
      label: 'Serial',
      getItems: (sshToken) => (sshToken.serial ? [sshToken.serial] : []),
      onClick: (sshToken) =>
        sshToken.serial ? this.selectToken(sshToken.serial) : () => {},
    }),
    new SimpleTableColumn({
      key: 'type',
      label: 'Type',
      getItems: (sshToken) => (sshToken.type ? [sshToken.type] : []),
    }),
  ];

  constructor(private machineService: MachineService) {}

  selectToken(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  getObjectStrings(options: object) {
    return Object.entries(options).map(([key, value]) => `${key}: ${value}`);
  }

  fetchDataHandler: FetchDataHandler = ({
    pageIndex,
    pageSize,
    sortby_sortdir,
    currentFilter,
  }) =>
    this.machineService.getToken({
      sortby: sortby_sortdir?.active,
      sortdir: sortby_sortdir?.direction,
      page: pageIndex,
      pageSize: pageSize,
      currentFilter: currentFilter,
      application: 'ssh',
    });

  processDataSource: ProcessDataSource<MachineTokenData> = (response: any) => [
    response.result.value.length,
    new MatTableDataSource(MachineTokenData.parseList(response.result.value)),
  ];
}
