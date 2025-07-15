import { linkedSignal, signal, WritableSignal } from '@angular/core';
import { of } from 'rxjs';
import { TokenApplication } from '../app/services/machine/machine.service';
import { MatTableDataSource } from '@angular/material/table';
import { TokenDetails } from '../app/services/token/token.service';
import { SelectionModel } from '@angular/cdk/collections';
import { UserData } from '../app/services/user/user.service';

export function makeResource<T>(initial: T) {
  return {
    value: signal(initial) as WritableSignal<T>,
    reload: jest.fn(),
    error: jest.fn().mockReturnValue(null),
  };
}

export class MockAuthService {
  role() {
    return 'admin';
  }

  isAuthenticatedUser() {
    return true;
  }

  user() {
    return 'alice';
  }
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

export class MockNotificationService {
  openSnackBar(message: string) {}
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

export class MockContentService {
  isProgrammaticTabChange = signal(false);
  selectedContent = signal('tokens');
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

export class MockMachineService {
  selectedApplicationType = signal<'ssh' | 'offline'>('ssh');
  tokenApplications: WritableSignal<TokenApplication[] | undefined> = signal<
    TokenApplication[] | undefined
  >([]);

  pageSize = jest.fn(() => 10);
  pageIndex = jest.fn(() => 0);
}

export class MockTableUtilsService {
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

export class NotificationService {
  openSnackBar = jest.fn();
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
