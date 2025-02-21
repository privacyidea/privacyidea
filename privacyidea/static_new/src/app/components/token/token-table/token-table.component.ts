import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatSortModule } from '@angular/material/sort';
import { TokenService } from '../../../services/token/token.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NotificationService } from '../../../services/notification/notification.service';
import {
  CellClickHandlerMap,
  FetchDataHandler,
  FetchResponseHandler,
  FilterKeywordHandlerMap,
  FilterTable,
} from '../../universals/filter-table/filter-table.component';
import { Observable } from 'rxjs/internal/Observable';

const columnsKeyMap = [
  { key: 'serial', label: 'Serial' },
  { key: 'tokentype', label: 'Type' },
  { key: 'active', label: 'Active' },
  { key: 'description', label: 'Description' },
  { key: 'failcount', label: 'Fail Counter' },
  { key: 'rollout_state', label: 'Rollout State' },
  { key: 'username', label: 'User' },
  { key: 'user_realm', label: 'User Realm' },
  { key: 'realms', label: 'Token Realm' },
  { key: 'container_serial', label: 'Container' },
];

@Component({
  selector: 'app-token-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    MatPaginatorModule,
    MatTableModule,
    MatSortModule,
    FilterTable,
  ],
  templateUrl: './token-table.component.html',
  styleUrl: './token-table.component.scss',
})
export class TokenTableComponent {
  apiFilter = this.tokenService.apiFilter;
  advancedApiFilter = this.tokenService.advancedApiFilter;

  @Input({ required: true }) tokenSerial!: WritableSignal<string>;
  @Input({ required: true }) containerSerial!: WritableSignal<string>;
  @Input({ required: true }) isProgrammaticChange!: WritableSignal<boolean>;
  @Input({ required: true }) selectedContent!: WritableSignal<string>;

  protected readonly columnsKeyMap = columnsKeyMap;

  constructor(
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    private notificationService: NotificationService,
  ) {}

  toggleActive(element: any): Observable<any> {
    var handler = this.tokenService.toggleActive(
      element.serial,
      element.active,
    );
    handler.subscribe({
      error: (error) => {
        console.error('Failed to toggle active.', error);
        this.notificationService.openSnackBar('Failed to toggle active.');
      },
    });
    return handler;
  }

  resetFailCount(element: any): Observable<any> {
    console.log('Resetting fail count for token:', element.serial);
    var handler = this.tokenService.resetFailCount(element.serial);
    handler.subscribe({
      error: (error) => {
        console.error('Failed to reset fail counter.', error);
        this.notificationService.openSnackBar('Failed to reset fail counter.');
      },
    });
    return handler;
  }

  tokenSelected(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }

  containerSelected(containerSerial: string) {
    this.isProgrammaticChange.set(true);
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }

  fetchDataHandler: FetchDataHandler = (
    pageIndex: number,
    pageSize: number,
    sortby_sortdir: any,
    filterValue: string,
  ) =>
    this.tokenService.getTokenData(
      pageIndex + 1,
      pageSize,
      sortby_sortdir,
      filterValue,
    );

  fetchResponseHandler: FetchResponseHandler = (response: any) => {
    const numItems = response.result.value.count;
    const dataSource = new MatTableDataSource(response.result.value.tokens);
    return [numItems, dataSource];
  };

  filterKeywordHandlerMap: FilterKeywordHandlerMap = [
    {
      key: 'active',
      handler: (filterValue: string) => {
        return this.tableUtilsService.toggleActiveInFilter(filterValue);
      },
    },
    {
      key: 'infokey & infovalue',
      handler: (filterValue: string) => {
        const result = this.tableUtilsService.toggleKeywordInFilter(
          filterValue,
          'infokey',
        );
        return this.tableUtilsService.toggleKeywordInFilter(
          result,
          'infovalue',
        );
      },
    },
  ];

  cellClickHandlerMap: CellClickHandlerMap = [
    {
      key: 'active',
      handler: (element: any) => {
        return this.toggleActive(element);
      },
    },
    {
      key: 'failcount',
      handler: (element: any) => {
        return this.resetFailCount(element);
      },
    },
    {
      key: 'serial',
      handler: (element: any) => {
        var observable: Observable<any> = new Observable((observer) => {
          this.tokenSelected(element.serial);
          observer.next();
          observer.complete();
        });
        return observable;
      },
    },
    {
      key: 'container_serial',
      handler: (element: any) => {
        var observable: Observable<any> = new Observable((observer) => {
          this.containerSelected(element.container_serial);
          observer.next();
          observer.complete();
        });
        return observable;
      },
    },
  ];
}
