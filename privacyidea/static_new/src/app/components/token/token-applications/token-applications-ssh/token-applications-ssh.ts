import { Component } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import {
  FetchDataHandler,
  FetchResponseHandler,
  FilterTable,
  SortDir,
} from '../../../universals/filter-table/filter-table.component';
import { MachineService } from '../../../../services/machine/machine.service';
import { filter } from 'rxjs';
import { KeywordFilter } from '../../../../services/keyword_filter';
import {
  SimpleTableColumn,
  TableColumn,
} from '../../../../services/table-utils/table-column';

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [MatTabsModule, FilterTable],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
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

  columns: TableColumn<SSHTokenData>[] = [
    new SimpleTableColumn({
      key: 'serial',
      label: 'Serial',
      getItems: (element) => [element.serial],
    }),
    new SimpleTableColumn({
      key: 'hostname',
      label: 'Hostname',
      getItems: (element) => [element.hostname],
    }),
    new SimpleTableColumn({
      key: 'machineid',
      label: 'Machine ID',
      getItems: (element) => [element.machine_id],
    }),
    new SimpleTableColumn({
      key: 'resolver',
      label: 'Resolver',
      getItems: (element) => [element.resolver],
    }),
    new SimpleTableColumn({
      key: 'options',
      label: 'Options',
      getItems: (element) => [element.options.service_id, element.options.user],
    }),
  ];

  fetchResponseHandler: FetchResponseHandler = (response: any) => {
    console.log('response', response);
    return [response.result.value.length, response.result.value];
  };

  constructor(private machineService: MachineService) {}

  splitFilters(filterValue: string) {
    var filterMap: { [key: string]: string } = {};
    var regexp = new RegExp(/\w+:\s\w+((?=\s)|$)/, 'g');
    var matches = filterValue.match(regexp);
    console.log('matches', matches);
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
    filterValue,
  }) => {
    var filterMap: { [key: string]: string } = {};
    if (filterValue) {
      filterMap = this.splitFilters(filterValue);
    }

    return this.machineService.getToken({
      serial: filterMap['serial'],
      hostname: filterMap['hostname'],
      machineid: filterMap['machineid'],
      resolver: filterMap['resolver'],
      service_id: filterMap['service_id'],
      user: filterMap['user'],
      page: pageIndex,
      pageSize: pageSize,
      sortby: sortby_sortdir?.active ?? 'serial',
      sortdir: sortby_sortdir?.direction ?? 'asc',
      application: 'ssh',
    });
  };
}

interface SSHTokenData {
  serial: string;
  hostname: string;
  machine_id: string;
  resolver: string;
  options: SSHTokenDataOptions;
}

type SSHTokenDataOptions = {
  service_id: string;
  user: string;
};

class SSHTokenData {
  serial: string;
  hostname: string;
  machine_id: string;
  resolver: string;
  options: SSHTokenDataOptions;

  constructor(data: SSHTokenData) {
    this.serial = data.serial;
    this.hostname = data.hostname;
    this.machine_id = data.machine_id;
    this.resolver = data.resolver;
    this.options = data.options;
  }
}
