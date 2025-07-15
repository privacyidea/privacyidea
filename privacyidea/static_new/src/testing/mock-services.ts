import { SelectionModel } from '@angular/cdk/collections';
import {
  HttpClient,
  HttpHeaders,
  HttpProgressEvent,
  HttpResourceRef,
} from '@angular/common/http';
import {
  computed,
  linkedSignal,
  Resource,
  ResourceStatus,
  Signal,
  signal,
  WritableSignal,
} from '@angular/core';
import { Sort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { Router } from '@angular/router';
import { Observable, of, Subscription } from 'rxjs';
import { PiResponse } from '../app/app.component';
import { TokenSelectedContentKey } from '../app/components/token/token.component';
import {
  AuthResponse,
  AuthRole,
  AuthService,
} from '../app/services/auth/auth.service';
import { ContentService } from '../app/services/content/content.service';
import { LocalService } from '../app/services/local/local.service';
import {
  Machines,
  MachineService,
  TokenApplication,
} from '../app/services/machine/machine.service';
import { NotificationServiceInterface } from '../app/services/notification/notification.service';
import {
  FilterPair,
  TableUtilsService,
} from '../app/services/table-utils/table-utils.service';
import { TokenDetails } from '../app/services/token/token.service';
import { UserData } from '../app/services/user/user.service';
import { VersionService } from '../app/services/version/version.service';

export function makeResource<T>(initial: T) {
  return {
    value: signal(initial) as WritableSignal<T>,
    reload: jest.fn(),
    error: jest.fn().mockReturnValue(null),
  };
}

export class MockHttpResourceRef<T> implements HttpResourceRef<T> {
  value: WritableSignal<T>;
  reload = jest.fn();
  error = signal<Error | null>(null);
  constructor(initial: T) {
    this.value = signal(initial) as WritableSignal<T>;
  }
  headers: Signal<HttpHeaders | undefined> = signal(undefined);
  statusCode: Signal<number | undefined> = signal(undefined);
  progress: Signal<HttpProgressEvent | undefined> = signal(undefined);
  hasValue(): this is HttpResourceRef<Exclude<T, undefined>> {
    return this.value() !== undefined;
  }
  destroy(): void {}
  set(value: T): void {
    this.value.set(value);
  }
  update(updater: (value: T) => T): void {
    this.value.set(updater(this.value()));
  }
  asReadonly(): Resource<T> {
    return {
      value: this.value,
      reload: this.reload,
      error: this.error,
      hasValue: this.hasValue.bind(this),
      status: signal(ResourceStatus.Resolved),
      isLoading: signal(false),
    };
  }
  status: Signal<ResourceStatus> = signal(ResourceStatus.Resolved);
  isLoading: Signal<boolean> = signal(false);
}

export class MockPiResponse<T> implements PiResponse<T, undefined> {
  id: number = 1;
  jsonrpc: string = '2.0';
  detail: undefined;
  result?:
    | {
        authentication?: 'CHALLENGE' | 'POLL' | 'PUSH';
        status: boolean;
        value?: T | undefined;
        error?: { code: number; message: string };
      }
    | undefined;
  signature: string = '';
  time: number = Date.now();
  version: string = '1.0';
  versionnumber: string = '1.0';

  static fromValue<T>(value: T): MockPiResponse<T> {
    const response = new MockPiResponse<T>();
    response.result = {
      status: true,
      value: value,
    };
    return response;
  }
}

export class MockAuthService implements AuthService {
  readonly authUrl = "environmentMock.proxyUrl + '/auth'";
  isAuthenticated: WritableSignal<boolean> = signal(true);
  user: WritableSignal<string> = signal('alice');
  realm: WritableSignal<string> = signal('default');
  role: WritableSignal<AuthRole> = signal('admin');
  menus: WritableSignal<string[]> = signal([
    'token_overview',
    'token_self-service_menu',
    'container_overview',
  ]);
  isSelfServiceUser: Signal<boolean> = signal(
    this.role() === 'user' && this.menus().includes('token_self-service_menu'),
  );
  authenticate(params: any): Observable<AuthResponse> {
    throw new Error('Method not implemented.');
  }
  acceptAuthentication(): void {
    throw new Error('Method not implemented.');
  }
  deauthenticate(): void {
    throw new Error('Method not implemented.');
  }
  // role() {
  //   return 'admin';
  // }

  isAuthenticatedUser() {
    return true;
  }

  constructor(
    readonly http: HttpClient = new HttpClient({} as any),
    readonly notificationService: NotificationServiceInterface = new MockNotificationService(),
    readonly versionService: VersionService = new VersionService(),
  ) {}

  // realm() {

  // user() {
  //   return 'alice';
  // }
}

export class MockUserService {
  selectedUserRealm = signal('');
  selectedUsername = signal('');
  userFilter = signal('');
  userNameFilter = jest.fn().mockReturnValue('');
  setDefaultRealm = jest.fn();
  filteredUsers = signal([]);
  selectedUser = signal<UserData | null>(null);

  resetUserSelection() {
    this.userFilter.set('');
    this.selectedUserRealm.set('');
  }
}

export class MockNotificationService implements NotificationServiceInterface {
  totalDuration = 5000;
  remainingTime: number = this.totalDuration;
  timerSub: Subscription = new Subscription();
  startTime: number = 0;

  openSnackBar = jest.fn().mockImplementation((message: string) => {
    // Simulate showing a notification
    console.log('Mock Notification:', message);
  });
}

export class MockValidateService {
  testToken() {
    return of(null);
  }
}

export class MockRealmService {
  realmOptions = signal(['realm1', 'realm2']);
  defaultRealm = signal('realm1');
  selectedRealms = signal<string[]>([]);
}

export class MockContentService implements ContentService {
  router: Router = {
    url: '/home',
    events: of({} as any),
  } as any;
  routeUrl: Signal<string> = signal('/home');
  selectedContent: WritableSignal<TokenSelectedContentKey> =
    signal('token_overview');
  tokenSerial: WritableSignal<string> = signal('');
  containerSerial: WritableSignal<string> = signal('');

  tokenSelected = jest.fn().mockImplementation((serial: string) => {
    this.selectedContent.set('token_details');
    this.tokenSerial.set(serial);
  });

  containerSelected = jest.fn().mockImplementation((serial: string) => {
    this.selectedContent.set('container_details');
    this.containerSerial.set(serial);
  });
  isProgrammaticTabChange = signal(false);
  constructor(public authService: MockAuthService = new MockAuthService()) {}
}

export class MockContainerService {
  #containerDetailSignal = signal({
    containers: [
      {
        serial: 'CONT-1',
        users: [
          {
            user_realm: '',
            user_name: '',
            user_resolver: '',
            user_id: '',
          },
        ],
        tokens: [],
        realms: [],
        states: [],
        type: '',
        select: '',
        description: '',
      },
    ],
    count: 1,
  });
  states = signal<string[]>([]);
  containerSerial = signal('CONT-1');
  containerDetailResource = makeResource({
    result: { value: { containers: [] } },
  });
  unassignContainer = jest.fn().mockReturnValue(of(null));
  assignContainer = jest.fn().mockReturnValue(of(null));
  containerDetail = this.#containerDetailSignal;
  getContainerData = jest.fn().mockReturnValue(
    of({
      result: {
        value: {
          containers: [
            {
              serial: 'CONT-1',
              users: [],
              tokens: [],
              realms: [],
              states: [],
              type: '',
              select: '',
              description: '',
            },
            {
              serial: 'CONT-2',
              users: [],
              tokens: [],
              realms: [],
              states: [],
              type: '',
              select: '',
              description: '',
            },
          ],
          count: 2,
        },
      },
    }),
  );
  selectedContainer = signal('');
  addTokenToContainer = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  unassignUser = jest.fn().mockReturnValue(of(null));
  setContainerRealm = jest.fn().mockReturnValue(of(null));
  setContainerDescription = jest.fn().mockReturnValue(of(null));
  deleteAllTokens = jest.fn().mockReturnValue(of(null));
  toggleAll = jest.fn().mockReturnValue(of(null));
  removeAll = jest.fn().mockReturnValue(of(null));
  removeTokenFromContainer = jest.fn().mockReturnValue(of(null));

  containerDetailFn = () => this.#containerDetailSignal();
}

export class MockTokenTableComponent {
  tokenSelection = new SelectionModel<any>(true, []);
  pageSizeOptions = signal([5, 10, 25, 50]);
}

export class MockOverflowService {
  private _overflow = false;

  getOverflowThreshold() {
    return 1920;
  }

  setWidthOverflow(value: boolean) {
    this._overflow = value;
  }

  isWidthOverflowing(selector: string, threshold: number) {
    return this._overflow;
  }

  isHeightOverflowing(selector: string, threshold: number) {
    return this._overflow;
  }
}

export class MockTokenService {
  showOnlyTokenNotInContainer = signal(false);
  tokenDetailResource = makeResource<{
    result: { value: { tokens: TokenDetails[] } };
  }>({
    result: {
      value: {
        tokens: [
          {
            tokentype: 'hotp',
            active: true,
            revoked: false,
            container_serial: 'CONT-1',
            realms: [],
            count: 0,
            count_window: 0,
            description: '',
            failcount: 0,
            id: 0,
            info: {},
            locked: false,
            maxfail: 0,
            otplen: 0,
            resolver: '',
            rollout_state: '',
            serial: '',
            sync_window: 0,
            tokengroup: [],
            user_id: '',
            user_realm: '',
            username: '',
          },
        ],
      },
    },
  });
  tokenSerial = signal('');
  filterValue = signal<Record<string, string>>({});
  pageIndex = signal(0);
  pageSize = signal(10);
  tokenTypeOptions: WritableSignal<string[]> = signal(['hotp', 'totp', 'push']);
  tokenSelection: WritableSignal<TokenDetails[]> = signal<TokenDetails[]>([]);
  defaultSizeOptions = signal([10, 25, 50, 100]);
  eventPageSize = 10;
  selectedTokenType = signal('hotp');

  tokenResource = makeResource({
    result: { value: { tokens: [], count: 0 } },
  });

  getTokenDetails = jest.fn().mockReturnValue(of({}));
  getRealms = jest.fn().mockReturnValue(of({ result: { value: [] } }));
  resetFailCount = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  unassignUser = jest.fn().mockReturnValue(of(null));
  toggleActive = jest.fn().mockReturnValue(of({}));

  getTokenData = this.getTokenDetails;
}

export class MockMachineService implements MachineService {
  filterParams = computed(() => {
    let allowedKeywords =
      this.selectedApplicationType() === 'ssh'
        ? [...this.sshApiFilter, ...this.sshAdvancedApiFilter]
        : [...this.offlineApiFilter, ...this.offlineAdvancedApiFilter];

    const filterPairs = Object.entries(this.filterValue())
      .map(([key, value]) => ({ key, value }))
      .filter(({ key }) => allowedKeywords.includes(key));
    if (filterPairs.length === 0) {
      return {};
    }
    let params: any = {};
    filterPairs.forEach(({ key, value }) => {
      if (['serial'].includes(key)) {
        params[key] = `*${value}*`;
      }
      if (['hostname', 'machineid', 'resolver'].includes(key)) {
        params[key] = value;
      }
      if (
        this.selectedApplicationType() === 'ssh' &&
        ['service_id'].includes(key)
      ) {
        params[key] = `*${value}*`;
      }
      if (
        this.selectedApplicationType() === 'offline' &&
        ['count', 'rounds'].includes(key)
      ) {
        params[key] = value;
      }
    });
    return params;
  });
  baseUrl: string = "environment.mockProxyUrl + '/machine/'";
  sshApiFilter: string[] = [];
  sshAdvancedApiFilter: string[] = [];
  offlineApiFilter: string[] = [];
  offlineAdvancedApiFilter: string[] = [];
  selectedContent: WritableSignal<TokenSelectedContentKey> =
    signal('token_applications');
  machinesResource = new MockHttpResourceRef(MockPiResponse.fromValue([]));

  machines: WritableSignal<Machines> = signal<Machines>([]);
  postAssignMachineToToken(args: {
    service_id: string;
    user: string;
    serial: string;
    application: string;
    machineid: string;
    resolver: string;
  }): Observable<any> {
    throw new Error('Mock method not implemented.');
  }
  filterValue: WritableSignal<Record<string, string>> = signal({});
  sort: WritableSignal<Sort> = signal({ active: '', direction: '' });
  tokenApplications: WritableSignal<TokenApplication[]> = signal([]);
  tokenApplicationResource: HttpResourceRef<
    PiResponse<TokenApplication[], undefined> | undefined
  > = new MockHttpResourceRef(MockPiResponse.fromValue([]));
  // postTokenOption(
  //   hostname: string,
  //   machineid: string,
  //   resolver: string,
  //   serial: string,
  //   application: string,
  //   mtid: string,
  // ): Observable<any> {
  //   throw new Error('Mock method not implemented.');
  // }
  postTokenOption = jest.fn().mockReturnValue(of({} as any));
  getAuthItem = jest.fn().mockReturnValue(
    of({
      result: {
        value: { serial: '', machineid: '', resolver: '' },
      },
    }),
  );
  postToken = jest.fn().mockReturnValue(of({} as any));
  getMachine = jest.fn().mockReturnValue(
    of({
      result: {
        value: {
          machines: [
            {
              hostname: 'localhost',
              machineid: 'machine1',
              resolver: 'resolver1',
              serial: 'serial1',
              type: 'ssh',
              applications: [],
            },
          ],
          count: 1,
        },
      },
    }),
  );
  deleteToken = jest.fn().mockReturnValue(of({} as any));
  deleteTokenMtid = jest.fn().mockReturnValue(of({} as any));
  onPageEvent = jest.fn();
  onSortEvent = jest.fn();
  selectedApplicationType = signal<'ssh' | 'offline'>('ssh');

  pageSize = signal(10);
  pageIndex = signal(0);

  constructor(
    public http: HttpClient = new HttpClient({} as any),
    public localService: LocalService = new LocalService(),
    public tableUtilsService: TableUtilsService = new MockTableUtilsService(),
    public contentService: ContentService = new MockContentService(),
  ) {}
}

export class MockTableUtilsService implements TableUtilsService {
  parseFilterString(
    filterValue: string,
    apiFilter: string[],
  ): { filterPairs: FilterPair[]; remainingFilterText: string } {
    throw new Error('Mock method not implemented.');
  }
  toggleKeywordInFilter(currentValue: string, keyword: string): string {
    throw new Error('Mock method not implemented.');
  }
  public toggleBooleanInFilter(args: {
    keyword: string;
    currentValue: string;
  }): string {
    throw new Error('Mock method not implemented.');
  }
  getSpanClassForKey(args: {
    key: string;
    value?: any;
    maxfail?: any;
  }): string {
    throw new Error('Mock method not implemented.');
  }
  getDivClassForKey(
    key: string,
  ): '' | 'details-scrollable-container' | 'details-value' {
    throw new Error('Mock method not implemented.');
  }
  getChildClassForColumnKey(columnKey: string): string {
    throw new Error('Mock method not implemented.');
  }
  getDisplayTextForKeyAndRevoked(
    key: string,
    value: any,
    revoked: boolean,
  ): string {
    throw new Error('Mock method not implemented.');
  }
  getTdClassForKey(key: string): string[] {
    throw new Error('Mock method not implemented.');
  }
  getSpanClassForState(state: string, clickable: boolean): string {
    throw new Error('Mock method not implemented.');
  }
  getDisplayTextForState(state: string): string {
    throw new Error('Mock method not implemented.');
  }
  handleColumnClick = jest.fn();
  getClassForColumnKey = jest.fn();
  isLink = jest.fn().mockReturnValue(false);
  getClassForColumn = jest.fn();
  getDisplayText = jest.fn();
  getTooltipForColumn = jest.fn();
  recordsFromText = jest.fn((filterString: string) => {
    const records: { [key: string]: string } = {};
    filterString.split(' ').forEach((part) => {
      const [key, value] = part.split(': ');
      if (key && value) {
        records[key] = value;
      }
    });
    return records;
  });
  emptyDataSource = jest
    .fn()
    .mockImplementation(
      (_pageSize: number, _columns: { key: string; label: string }[]) => {
        const dataSource = new MatTableDataSource<TokenApplication>([]);
        (dataSource as any).isEmpty = true;
        return dataSource;
      },
    );
}

export class MockAuditService {
  apiFilter = ['user', 'success'];
  advancedApiFilter = ['machineid', 'resolver'];

  filterValue = signal<Record<string, string>>({});
  auditResource = {
    value: signal({ result: { value: { count: 0, auditdata: [] } } }),
  };
  pageSize = linkedSignal({
    source: this.filterValue,
    computation: () => 10,
  });

  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize(),
    }),
    computation: () => 0,
  });
}
