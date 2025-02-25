import { Component } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import {
  CellClickHandlerMap,
  FetchDataHandler,
  FetchResponseHandler,
  FilterKeywordHandlerMap,
  FilterTable,
  SortDir,
} from '../../../universals/filter-table/filter-table.component';
import { MachineService } from '../../../../services/machine/machine.service';
import { filter } from 'rxjs';

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [MatTabsModule, FilterTable],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
  apiFilter = [
    'serial',
    'hostname',
    'machineid',
    'resolver',
    'rounds',
    'count',
    'application',
  ];
  columnsKeyMap = [
    { key: 'serial', label: 'Serial' },
    { key: 'hostname', label: 'Hostname' },
    { key: 'machineid', label: 'Machine ID' },
    { key: 'resolver', label: 'Resolver' },
    { key: 'rounds', label: 'Rounds' },
    { key: 'count', label: 'Count' },
    { key: 'application', label: 'Application' },
  ];

  filterKeywordHandlerMap: FilterKeywordHandlerMap = [];
  cellClickHandlerMap: CellClickHandlerMap = [];
  fetchResponseHandler: FetchResponseHandler = (response: any) => {
    return [response.count, response.data];
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

  fetchDataHandler: FetchDataHandler = (
    pageIndex: number,
    pageSize: number,
    sortby_sortdir: SortDir,
    filterValue: string,
  ) => {
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
      sortby: sortby_sortdir?.active,
      sortdir: sortby_sortdir?.direction,
      application: filterMap['application'],
    });
  };
}
