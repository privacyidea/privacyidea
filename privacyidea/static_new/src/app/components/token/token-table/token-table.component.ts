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
  FetchDataHandler,
  FetchDataResponse,
  FilterTable,
  ProcessDataSource,
} from '../../universals/filter-table/filter-table.component';
import { Observable } from 'rxjs/internal/Observable';
import { KeywordFilter } from '../../../services/keyword_filter';
import {
  OnClickTableColumn,
  SimpleTableColumn,
  TableColumn,
} from '../../../services/table-utils/table-column';
import { TokenData } from '../../../model/token/token-data';
import { TokenSelectedContent } from '../token.component';
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
  basicFilters: KeywordFilter[] = [
    new KeywordFilter({ key: 'serial', label: 'Serial' }),
    new KeywordFilter({ key: 'type', label: 'Type' }),
    new KeywordFilter({
      key: 'active',
      label: 'Active',
      toggle: (filterValue: string) => KeywordFilter.toggleActive(filterValue),
      iconName: (filterValue: string) => {
        const value = KeywordFilter.getValue({
          keyword: 'active',
          filterValue,
        });
        if (value === 'true') return 'change_circle';
        if (value === 'false') return 'remove_circle';
        return 'add_circle';
      },
    }),
    new KeywordFilter({ key: 'description', label: 'Description' }),
    new KeywordFilter({ key: 'rollout_state', label: 'Rollout State' }),
    new KeywordFilter({ key: 'user', label: 'User' }),
    new KeywordFilter({ key: 'tokenrealm', label: 'Token Realm' }),
    new KeywordFilter({ key: 'container_serial', label: 'Container' }),
  ];
  advancedFilters: KeywordFilter[] = [
    new KeywordFilter({
      key: 'infokey & infovalue',
      label: 'Infokey & Infovalue',
      isSelected: (filterValue) => {
        const regexKey = new RegExp(/\binfokey:/, 'i');
        const regexValue = new RegExp(/\binfovalue:/, 'i');
        return regexKey.test(filterValue) || regexValue.test(filterValue);
      },
      toggle: (filterValue: string) => {
        const result = KeywordFilter.defaultToggler({
          filterValue: filterValue,
          keyword: 'infokey',
        });
        return KeywordFilter.defaultToggler({
          filterValue: result,
          keyword: 'infovalue',
        });
      },
    }),
    new KeywordFilter({ key: 'userid', label: 'User ID' }),
    new KeywordFilter({ key: 'resolver', label: 'Resolver' }),
    new KeywordFilter({ key: 'assigned', label: 'Assigned' }),
  ];
  @Input({ required: true }) tokenSerial!: WritableSignal<string>;
  @Input({ required: true }) containerSerial!: WritableSignal<string>;
  @Input({ required: true }) isProgrammaticChange!: WritableSignal<boolean>;
  @Input({ required: true })
  selectedContent!: WritableSignal<TokenSelectedContent>;
  columns: TableColumn<TokenData>[] = [
    new OnClickTableColumn({
      key: 'serial',
      label: 'Serial',
      getItems: (token) => (token.serial ? [token.serial] : []),
      onClick: (token) =>
        token.serial ? this.selectToken(token.serial) : null,
    }),
    new SimpleTableColumn({
      key: 'tokentype',
      label: 'Type',
      getItems: (token: TokenData) =>
        token.tokentype ? [token.tokentype] : [],
    }),
    new OnClickTableColumn({
      key: 'active',
      label: 'Active',
      getItems: (token) =>
        typeof token.active !== 'boolean'
          ? []
          : token.revoked
            ? ['revoked']
            : token.locked
              ? ['locked']
              : token.active
                ? ['active']
                : ['deactivated'],
      getNgClass: (token) =>
        typeof token.active !== 'boolean'
          ? ''
          : token.active
            ? 'highlight-true-clickable'
            : 'highlight-false-clickable',

      onClick: (token) => this.toggleActive(token),
    }),
    new SimpleTableColumn({
      key: 'description',
      label: 'Description',
      getItems: (token) => (token.description ? [token.description] : []),
    }),
    new OnClickTableColumn({
      key: 'failcount',
      label: 'Fail Counter',
      getItems: (token) =>
        typeof token.failcount !== 'number' ? [] : [token.failcount.toString()],
      getNgClass: (token) =>
        typeof token.failcount !== 'number'
          ? ''
          : token.failcount === 0
            ? 'highlight-true'
            : token.failcount >= 1 && token.failcount < 3
              ? 'highlight-warning-clickable'
              : 'highlight-false-clickable',
      onClick: (token) => this.resetFailCount(token),
    }),
    new SimpleTableColumn({
      key: 'rollout_state',
      label: 'Rollout State',
      getItems: (token) => (token.rollout_state ? [token.rollout_state] : []),
    }),
    new SimpleTableColumn({
      key: 'username',
      label: 'User',
      getItems: (token) => (token.username ? [token.username] : []),
    }),
    new SimpleTableColumn({
      key: 'user_realm',
      label: 'User Realm',
      getItems: (token) => (token.user_realm ? [token.user_realm] : []),
    }),
    new SimpleTableColumn({
      key: 'realms',
      label: 'Token Realm',
      getNgClass: (token) =>
        token.realms && token.realms.length > 1 ? 'realm-list' : 'realm',
      getItems: (token) => (token.realms ? [token.realms] : []),
    }),
    new OnClickTableColumn({
      key: 'container_serial',
      label: 'Container',
      getItems: (token) =>
        token.container_serial ? [token.container_serial] : [],
      onClick: (token) =>
        token.container_serial
          ? this.containerSelected(token.container_serial)
          : null,
    }),
  ];

  constructor(
    protected tokenService: TokenService,
    protected tableUtilsService: TableUtilsService,
    private notificationService: NotificationService,
  ) {}

  toggleActive(element: TokenData): Observable<any> {
    const { serial, active } = element;
    if (serial === undefined || active === undefined) {
      console.error('Failed to toggle active. Missing serial or active.');
      return new Observable();
    }
    var handler = this.tokenService.toggleActive(serial, active);
    handler.subscribe({
      error: (error) => {
        console.error('Failed to toggle active.', error);
        this.notificationService.openSnackBar('Failed to toggle active.');
      },
    });
    return handler;
  }
  resetFailCount(element: any): Observable<any> {
    var handler = this.tokenService.resetFailCount(element.serial);
    handler.subscribe({
      error: (error) => {
        console.error('Failed to reset fail counter.', error);
        this.notificationService.openSnackBar('Failed to reset fail counter.');
      },
    });
    return handler;
  }
  selectToken(serial: string) {
    this.tokenSerial.set(serial);
    this.selectedContent.set('token_details');
  }
  containerSelected(containerSerial: string) {
    this.isProgrammaticChange.set(true);
    this.containerSerial.set(containerSerial);
    this.selectedContent.set('container_details');
  }

  fetchDataHandler: FetchDataHandler = ({
    pageIndex,
    pageSize,
    sortby_sortdir,
    filterValue: currentFilter,
  }): Observable<any> =>
    this.tokenService.getTokenData(
      pageIndex + 1,
      pageSize,
      sortby_sortdir,
      currentFilter,
    );

  processDataSource: ProcessDataSource<TokenData> = (
    response: FetchDataResponse,
  ) => [
    response.result.value.count,
    new MatTableDataSource(TokenData.parseList(response.result.value.tokens)),
  ];
}
