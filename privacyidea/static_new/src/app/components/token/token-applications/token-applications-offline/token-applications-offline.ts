import { Component, Input, WritableSignal } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import {
  FetchDataHandler,
  FilterTable,
  SortDir,
  ProcessDataSource,
  FetchDataResponse,
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
import { TokenSelectedContent } from '../../token.component';

@Component({
  selector: 'app-token-applications-offline',
  standalone: true,
  imports: [MatTabsModule, FilterTable],
  templateUrl: './token-applications-offline.html',
  styleUrls: ['./token-applications-offline.scss'],
})
export class TokenApplicationsOffline {
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;
  @Input({ required: true })
  selectedContent!: WritableSignal<TokenSelectedContent>;

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
    new SimpleTableColumn({
      key: 'id',
      label: 'ID',
      getItems: (offlineToken) =>
        offlineToken.id ? [offlineToken.id.toString()] : [],
    }),
    new SimpleTableColumn({
      key: 'machine_id',
      label: 'Machine ID',
      getItems: (offlineToken) =>
        offlineToken.machine_id ? [offlineToken.machine_id] : [],
    }),
    new SimpleTableColumn({
      key: 'options',
      label: 'Options',
      getItems: (offlineToken) =>
        offlineToken.options ? this.getObjectStrings(offlineToken.options) : [],
    }),
    new SimpleTableColumn({
      key: 'resolver',
      label: 'Resolver',
      getItems: (offlineToken) =>
        offlineToken.resolver ? [offlineToken.resolver] : [],
    }),
    new OnClickTableColumn({
      key: 'serial',
      label: 'Serial',
      getItems: (offlineToken) =>
        offlineToken.serial ? [offlineToken.serial] : [],
      onClick: (offlineToken) =>
        offlineToken.serial ? this.selectToken(offlineToken.serial) : undefined,
    }),
    new SimpleTableColumn({
      key: 'type',
      label: 'Type',
      getItems: (offlineToken) =>
        offlineToken.type ? [offlineToken.type] : [],
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

  splitFilters(filterValue: string) {
    var filterMap: { [key: string]: string } = {};
    var regexp = new RegExp(/\w+:\s\w+((?=\s)|$)/, 'g');
    var matches = filterValue.match(regexp);
    if (matches) {
      matches.forEach((match) => {
        var [key, value] = match.split(': ');
        filterMap[key] = value;
      });
    }

    return filterMap;
  }

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
    response.result.value.length,
    new MatTableDataSource(MachineTokenData.parseList(response.result.value)),
  ];
}
