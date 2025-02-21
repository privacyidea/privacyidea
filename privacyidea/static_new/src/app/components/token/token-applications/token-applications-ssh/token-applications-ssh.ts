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

@Component({
  selector: 'app-token-applications-ssh',
  standalone: true,
  imports: [MatTabsModule, FilterTable],
  templateUrl: './token-applications-ssh.html',
  styleUrls: ['./token-applications-ssh.scss'],
})
export class TokenApplicationsSsh {
  apiFilter = ['serial', 'service_id', 'user'];
  columnsKeyMap = [
    { key: 'serial', label: 'Serial' },
    { key: 'service_id', label: 'Service ID' },
    { key: 'user', label: 'User' },
  ];

  filterKeywordHandlerMap: FilterKeywordHandlerMap = [];
  cellClickHandlerMap: CellClickHandlerMap = [];
  fetchResponseHandler: FetchResponseHandler = (response: any) => {
    return [response.count, response.data];
  };

  constructor(private machineService: MachineService) {}

  fetchDataHandler: FetchDataHandler = (
    pageIndex: number,
    pageSize: number,
    sortby_sortdir: SortDir,
    filterValue: string,
  ) =>
    this.machineService
      .getMachineToken
      //   pageIndex,
      //   pageSize,
      //   sortby_sortdir,
      //   filterValue + ' tokenType: ssh',
      ();

  /*

                  <app-token-applications
                  [apiFilter]="['serial', 'service_id', 'user']"
                  [columnsKeyMap]="columnsKeyMap"
                  [fetchDataHandler]="fetchDataHandler"
                  [fetchResponseHandler]="fetchResponseHandler" />
    columnsKeyMap

    toggleKeywordInFilterHandler
    cellClickHandlerMap
    fetchDataHandler
    fetchResponseHandler
    */
}
