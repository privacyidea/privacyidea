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
  FetchResponseHandler,
  FilterTable,
} from '../../universals/filter-table/filter-table.component';
import { Observable } from 'rxjs/internal/Observable';
import { KeywordFilter } from '../../../services/keyword_filter';
import {
  OnClickTableColumn,
  SimpleTableColumn,
  TableColumn,
} from '../../../services/table-utils/table-column';

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
      toggle: (filterValue: string) => {
        return KeywordFilter.toggleActive(filterValue);
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
        const regexKey = new RegExp(`\\binfokey:`, 'i');
        const regexValue = new RegExp(`\\binfovalue:`, 'i');
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
  @Input({ required: true }) selectedContent!: WritableSignal<string>;

  columns: TableColumn<TokenData>[] = [
    new OnClickTableColumn({
      key: 'serial',
      label: 'Serial',
      getItems: (token) => (token.serial ? [token.serial] : []),

      onClick: (token) =>
        token.serial ? this.tokenSelected(token.serial) : null,
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

      getItems: (token) => {
        if (token.active === undefined || token.active === null) {
          return [];
        }
        if (token.revoked) {
          return ['revoked'];
        } else if (token.locked) {
          return ['locked'];
        } else if (token.active) {
          return ['active'];
        } else {
          return ['deactivated'];
        }
      },
      //       if (element['active'] === '') {
      //   return '';
      // }
      // if (element['locked']) {
      //   return 'highlight-false-clickable';
      // } else if (element['revoked']) {
      //   return 'highlight-false-clickable';
      // } else if (element['active'] === false) {
      //   return 'highlight-false-clickable';
      // } else {
      //   return 'highlight-true-clickable';
      // }
      getNgClass: (token) => {
        if (token.active === undefined || token.active === null) {
          return '';
        }
        return token.active
          ? 'highlight-true-clickable'
          : 'highlight-false-clickable';
      },
      onClick: (token) => {
        return this.toggleActive(token);
      },
    }),
    new SimpleTableColumn({
      key: 'description',
      label: 'Description',
      getItems: (token) => {
        return token.description ? [token.description] : [];
      },
    }),

    new OnClickTableColumn({
      key: 'failcount',
      label: 'Fail Counter',
      getItems: (token) => {
        return token.failcount ? [token.failcount.toString()] : ['0'];
      },
      getNgClass: (token) => {
        if (token.failcount === undefined) {
          return '';
        } else if (token.failcount === 0) {
          return 'highlight-true';
        } else if (token.failcount >= 1 && token.failcount < 3) {
          return 'highlight-warning-clickable';
        } else {
          return 'highlight-false-clickable';
        }
      },
      onClick: (token) => {
        return this.resetFailCount(token);
      },
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
    console.log('Toggling active for token:', element.serial);
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

  fetchDataHandler: FetchDataHandler = ({
    pageIndex,
    pageSize,
    sortby_sortdir,
    filterValue,
  }) =>
    this.tokenService.getTokenData(
      pageIndex + 1,
      pageSize,
      sortby_sortdir,
      filterValue,
    );

  fetchResponseHandler: FetchResponseHandler = (response: any) => {
    const numItems = response.result.value.count;
    const dataSource = new MatTableDataSource<TokenData>(
      TokenData.parseList(response.result.value.tokens),
    );
    return [numItems, dataSource];
  };
}

class TokenData {
  serial?: string;
  tokentype?: string;
  active?: boolean;
  description?: string;
  failcount?: number;
  rollout_state?: string;
  username?: string;
  user_realm?: string;
  realms?: string;
  container_serial?: string;
  revoked?: boolean;
  locked?: boolean;

  constructor(data: any) {
    this.serial = data.serial;
    this.tokentype = data.tokentype;
    this.active = data.active;
    this.description = data.description;
    this.failcount = data.failcount;
    this.rollout_state = data.rollout_state;
    this.username = data.username;
    this.user_realm = data.user_realm;
    this.realms = data.realms;
    this.container_serial = data.container_serial;
    this.revoked = data.revoked;
    this.locked = data.locked;
  }

  static parseList(tokens: any[]): TokenData[] {
    return tokens.map((token) => {
      return new TokenData(token);
    });
  }
}
