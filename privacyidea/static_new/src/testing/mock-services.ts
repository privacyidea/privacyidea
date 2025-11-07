/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { Audit, AuditServiceInterface } from "../app/services/audit/audit.service";
import { AuthData, AuthDetail, AuthResponse, AuthRole } from "../app/services/auth/auth.service";
import {
  ContainerDetailData,
  ContainerDetails,
  ContainerRegisterData,
  ContainerService,
  ContainerServiceInterface,
  ContainerTemplate,
  ContainerType,
  ContainerTypes
} from "../app/services/container/container.service";
import { HttpHeaders, HttpParams, HttpProgressEvent, HttpResourceRef } from "@angular/common/http";
import {
  BulkResult,
  LostTokenResponse,
  TokenDetails,
  TokenGroups,
  TokenImportResult,
  Tokens,
  TokenService,
  TokenServiceInterface,
  TokenType
} from "../app/services/token/token.service";
import { Machines, MachineServiceInterface, TokenApplication } from "../app/services/machine/machine.service";
import { Observable, of, Subject, Subscription } from "rxjs";
import { Realm, Realms, RealmServiceInterface } from "../app/services/realm/realm.service";
import {
  computed,
  inject,
  linkedSignal,
  Resource,
  ResourceStatus,
  Signal,
  signal,
  WritableSignal
} from "@angular/core";
import { UserData, UserServiceInterface } from "../app/services/user/user.service";
import { ValidateCheckResponse, ValidateServiceInterface } from "../app/services/validate/validate.service";
import { ContentServiceInterface } from "../app/services/content/content.service";
import { FilterValue } from "../app/core/models/filter_value";
import { LocalServiceInterface } from "../app/services/local/local.service";
import { MatTableDataSource } from "@angular/material/table";
import { NotificationServiceInterface } from "../app/services/notification/notification.service";
import { OverflowServiceInterface } from "../app/services/overflow/overflow.service";
import { PiResponse } from "../app/app.component";
import { Router } from "@angular/router";
import { Sort } from "@angular/material/sort";
import { TableUtilsServiceInterface } from "../app/services/table-utils/table-utils.service";
import { TokenEnrollmentLastStepDialogData } from "../app/components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { TokenTypeOption } from "../app/components/token/token.component";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../app/mappers/token-api-payload/_token-api-payload.mapper";

export function makeResource<T>(initial: T) {
  return {
    value: signal(initial) as WritableSignal<T>,
    reload: jest.fn(),
    error: jest.fn().mockReturnValue(null)
  };
}
const assert = (condition: boolean, message: string) => {
  if (!condition) {
    throw new Error(message);
  }
};
export class MockAuthData implements AuthData {
  log_level = 0;
  menus = [];
  realm = "";
  rights = [];
  role: AuthRole = "";
  token = "";
  username = "";
  logout_time = 0;
  audit_page_size = 10;
  token_page_size = 10;
  user_page_size = 10;
  policy_template_url = "";
  default_tokentype = "";
  default_container_type = "";
  user_details = false;
  token_wizard = false;
  token_wizard_2nd = false;
  admin_dashboard = false;
  dialog_no_token = false;
  search_on_enter = false;
  timeout_action = "";
  token_rollover: any = null;
  hide_welcome = false;
  hide_buttons = false;
  deletion_confirmation = false;
  show_seed = false;
  show_node = "";
  subscription_status = 0;
  subscription_status_push = 0;
  qr_image_android: string | null = null;
  qr_image_ios: string | null = null;
  qr_image_custom: string | null = null;
  logout_redirect_url = "";
  require_description = [];
  rss_age = 0;
  container_wizard = {
    enabled: false,
    type: "",
    registration: false,
    template: null
  };
  versionnumber = "";
}
export class MockAuthDetail implements AuthDetail {
  username = "";
}
export class MockHttpResourceRef<T> implements HttpResourceRef<T> {
  value: WritableSignal<T>;
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
      isLoading: signal(false)
    };
  }
  headers: Signal<HttpHeaders | undefined> = signal(undefined);
  statusCode: Signal<number | undefined> = signal(undefined);
  progress: Signal<HttpProgressEvent | undefined> = signal(undefined);
  hasValue(): this is HttpResourceRef<Exclude<T, undefined>> {
    return this.value() !== undefined;
  }
  destroy(): void {}
  status: Signal<ResourceStatus> = signal(ResourceStatus.Resolved);
  error = signal<Error | null>(null);
  isLoading: Signal<boolean> = signal(false);
  reload = jest.fn();
  constructor(initial: T) {
    this.value = signal(initial) as WritableSignal<T>;
  }
}
export class MockBase64Service {
  base64URLToBytes = jest.fn((_: string) => new Uint8Array([1, 2]));
  bytesToBase64 = jest.fn(() => "b64");
}
export class MockPiResponse<Value, Detail = unknown> implements PiResponse<Value, Detail> {
  error?: {
    code: number;
    message: string;
  };
  id: number;
  jsonrpc: string;
  detail: Detail;
  result?: {
    authentication?: "CHALLENGE" | "POLL" | "PUSH";
    status: boolean;
    value?: Value;
    error?: {
      code: number;
      message: string;
    };
  };
  signature: string;
  time: number;
  version: string;
  versionnumber: string;
  constructor(args: {
    detail: Detail;
    result?: {
      authentication?: "CHALLENGE" | "POLL" | "PUSH";
      status: boolean;
      value?: Value;
      error?: { code: number; message: string };
    };
    error?: {
      code: number;
      message: string;
    };
    id?: number;
    jsonrpc?: string;
    signature?: string;
    time?: number;
    version?: string;
    versionnumber?: string;
  }) {
    this.detail = args.detail;
    this.result = args.result;
    this.error = args.error;
    this.id = args.id ?? 0;
    this.jsonrpc = args.jsonrpc ?? "2.0";
    this.signature = args.signature ?? "";
    this.time = args.time ?? Date.now();
    this.version = args.version ?? "1.0";
    this.versionnumber = args.versionnumber ?? "1.0";
  }
  static fromValue<Value, Detail = unknown>(
    value: Value,
    detail: Detail = {} as Detail
  ): MockPiResponse<Value, Detail> {
    return new MockPiResponse<Value, Detail>({
      detail,
      result: { status: true, value }
    });
  }
}

export class MockUserService implements UserServiceInterface {
  usersOfRealmResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  selectedUsername = signal("");
  setDefaultRealm = jest.fn();
  selectedUser = signal<UserData | null>(null);

  resetFilter = jest.fn().mockImplementation(() => {
    this.apiUserFilter.set(new FilterValue());
  });

  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    const inputElement = $event.target as HTMLInputElement;
    this.apiUserFilter.set(new FilterValue({ value: inputElement.value }));
  });

  apiUserFilter: WritableSignal<FilterValue> = signal(new FilterValue());

  pageIndex: WritableSignal<number> = signal(0);

  pageSize: WritableSignal<number> = signal(10);
  apiFilterOptions: string[] = [];
  advancedApiFilterOptions: string[] = [];
  userResource: HttpResourceRef<PiResponse<UserData[]> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  user: WritableSignal<UserData> = signal({
    description: "",
    editable: false,
    email: "",
    givenname: "",
    mobile: "",
    phone: "",
    resolver: "",
    surname: "",
    userid: "",
    username: ""
  });
  usersResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  users: WritableSignal<UserData[]> = signal([]);
  allUsernames: Signal<string[]> = signal([]);

  selectionFilteredUsernames: Signal<string[]> = signal([]);
  selectedUserRealm = signal("");

  selectionFilter = linkedSignal<string, UserData | string>({
    source: this.selectedUserRealm,
    computation: () => ""
  });
  selectionUsernameFilter = linkedSignal<string>(() => {
    const filter = this.selectionFilter();
    if (typeof filter === "string") {
      return filter;
    }
    return filter?.username ?? "";
  });

  selectionFilteredUsers = signal([]);
  displayUser = jest.fn().mockImplementation((username: string, realm: string) => {
    this.selectedUsername.set(username);
    this.selectedUserRealm.set(realm);
    const user = this.users().find((u) => u.username === username && u.resolver === realm) || null;
    this.selectedUser.set(user);
  });
  resetUserSelection() {
    this.selectionFilter.set("");
    this.selectedUserRealm.set("");
  }
}
export class MockNotificationService implements NotificationServiceInterface {
  totalDuration = 5000;
  remainingTime: number = this.totalDuration;
  timerSub: Subscription = new Subscription();
  startTime: number = 0;
  openSnackBar = jest.fn().mockImplementation((message: string) => {
    // Simulate showing a notification
  });
}
export class MockValidateService implements ValidateServiceInterface {
  testToken(tokenSerial: string, otpOrPinToTest: string, otponly?: string): Observable<ValidateCheckResponse> {
    return of({
      id: 1,
      jsonrpc: "2.0",
      result: {
        status: true,
        value: true
      },
      detail: {},
      signature: "",
      time: Date.now(),
      version: "1.0",
      versionnumber: "1.0"
    });
  }
  authenticatePasskey(args?: { isTest?: boolean }): Observable<AuthResponse> {
    return of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail()));
  }
  authenticateWebAuthn(args: {
    signRequest: any;
    transaction_id: string;
    username: string;
    isTest?: boolean;
  }): Observable<AuthResponse> {
    return of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail()));
  }
  pollTransaction(transactionId: string): Observable<boolean> {
    return of(true);
  }
}
export class MockRealmService implements RealmServiceInterface {
  selectedRealms = signal<string[]>([]);
  realmResource = new MockHttpResourceRef(MockPiResponse.fromValue<Realms>({}));
  realmOptions = signal(["realm1", "realm2"]);
  defaultRealmResource = new MockHttpResourceRef(MockPiResponse.fromValue<Realms>({}));
  defaultRealm = signal("realm1");
}
export class MockContentService implements ContentServiceInterface {
  router: Router = {
    url: "/home",
    events: of({} as any)
  } as any;
  routeUrl: WritableSignal<string> = signal("/home");
  previousUrl: Signal<string> = signal("/home");
  isProgrammaticTabChange = signal(false);
  tokenSerial: WritableSignal<string> = signal("");
  containerSerial: WritableSignal<string> = signal("");
  tokenSelected = jest.fn().mockImplementation((serial: string) => {
    this.tokenSerial.set(serial);
  });
  containerSelected = jest.fn().mockImplementation((serial: string) => {
    this.containerSerial.set(serial);
  });
}
export class MockContainerService implements ContainerServiceInterface {
  selectedContainerType: Signal<ContainerType> = signal<ContainerType>({
    containerType: "generic",
    description: "",
    token_types: []
  });
  containerDetail: WritableSignal<ContainerDetails> = signal({
    containers: [],
    count: 0
  });

  addToken: (tokenSerial: string, containerSerial: string) => Observable<any> = jest.fn();
  removeToken: (tokenSerial: string, containerSerial: string) => Observable<any> = jest.fn();
  handleFilterInput = jest.fn().mockReturnValue(of({}));
  clearFilter = jest.fn().mockReturnValue(of({}));
  containerBelongsToUser = jest.fn().mockReturnValue(true);
  #containerDetailSignal = signal({
    containers: [
      {
        serial: "CONT-1",
        users: [
          {
            user_realm: "",
            user_name: "",
            user_resolver: "",
            user_id: ""
          }
        ],
        tokens: [],
        realms: [],
        states: [],
        type: "",
        select: "",
        description: ""
      }
    ],
    count: 1
  });
  apiFilter: string[] = [];
  advancedApiFilter: string[] = [];
  stopPolling$: Subject<void> = new Subject<void>();
  containerBaseUrl: string = "mockEnvironment.proxyUrl + '/container'";
  eventPageSize: number = 10;
  states = signal<string[]>([]);
  containerSerial = signal("CONT-1");
  selectedContainer = signal("");
  sort: WritableSignal<Sort> = signal({ active: "serial", direction: "asc" });
  containerFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  filterParams: Signal<Record<string, string>> = computed(() =>
    Object.fromEntries(
      Object.entries(this.containerFilter()).filter(([key]) =>
        [...this.apiFilter, ...this.advancedApiFilter].includes(key)
      )
    )
  );
  pageSize: WritableSignal<number> = signal(10);
  pageIndex: WritableSignal<number> = signal(0);
  loadAllContainers: Signal<boolean> = signal(false);
  containerResource: HttpResourceRef<PiResponse<ContainerDetails> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue({
      containers: [],
      count: 0
    })
  );
  containerOptions: WritableSignal<string[]> = signal([]);
  filteredContainerOptions: Signal<string[]> = computed(() => {
    const options = this.containerOptions();
    const filter = this.containerFilter();
    return options.filter((option) => option.includes(filter.value) || option.includes(filter.hiddenValue));
  });
  containerSelection: WritableSignal<ContainerDetailData[]> = signal([]);
  containerTypesResource: HttpResourceRef<PiResponse<ContainerTypes, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue<ContainerTypes>(new Map())
  );
  containerTypeOptions: Signal<ContainerType[]> = computed(() => {
    return [
      { containerType: "generic", description: "", token_types: [] } as ContainerType,
      { containerType: "smartphone", description: "", token_types: [] } as ContainerType,
      { containerType: "yubikey", description: "", token_types: [] } as ContainerType
    ];
  });
  containerDetailResource = new MockHttpResourceRef(
    MockPiResponse.fromValue({
      containers: [
        {
          serial: "CONT-1",
          users: [
            {
              user_realm: "",
              user_name: "",
              user_resolver: "",
              user_id: ""
            }
          ],
          tokens: [],
          realms: [],
          states: [],
          type: "",
          select: "",
          description: ""
        }
      ],
      count: 1
    })
  );
  templatesResource: HttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined> =
    new MockHttpResourceRef(
      MockPiResponse.fromValue<{ templates: ContainerTemplate[] }>({
        templates: []
      })
    );
  templates: WritableSignal<ContainerTemplate[]> = signal([]);
  assignContainer = jest.fn().mockReturnValue(of(null));
  unassignContainer = jest.fn().mockReturnValue(of(null));
  setContainerRealm = jest.fn().mockReturnValue(of(null));
  setContainerDescription = jest.fn().mockReturnValue(of(null));
  toggleActive = jest.fn().mockReturnValue(of({}));
  unassignUser = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  setContainerInfos = jest.fn().mockReturnValue(of({}));
  deleteInfo = jest.fn().mockReturnValue(of({}));
  addTokenToContainer = jest.fn().mockReturnValue(of(null));
  removeTokenFromContainer = jest.fn().mockReturnValue(of(null));
  toggleAll = jest.fn().mockReturnValue(of(null));
  removeAll = jest.fn().mockReturnValue(of(null));
  deleteContainer = jest.fn().mockReturnValue(of({}));
  deleteAllTokens = jest.fn().mockReturnValue(of(null));
  registerContainer(params: {
    container_serial: string;
    passphrase_prompt: string;
    passphrase_response: string;
  }): Observable<PiResponse<ContainerRegisterData, unknown>> {
    throw new Error("Method not implemented.");
  }
  stopPolling(): void {
    throw new Error("Method not implemented.");
  }
  createContainer(param: {
    container_type: string;
    description?: string;
    user_realm?: string;
    template?: string;
    user?: string;
    realm?: string;
    options?: any;
  }): Observable<PiResponse<{ container_serial: string }, unknown>> {
    throw new Error("Method not implemented.");
  }
  pollContainerRolloutState(
    containerSerial: string,
    startTime: number
  ): Observable<PiResponse<ContainerDetails, unknown>> {
    throw new Error("Method not implemented.");
  }
  getContainerData = jest.fn().mockReturnValue(
    of({
      result: {
        value: {
          containers: [
            {
              serial: "CONT-1",
              users: [],
              tokens: [],
              realms: [],
              states: [],
              type: "",
              select: "",
              description: ""
            },
            {
              serial: "CONT-2",
              users: [],
              tokens: [],
              realms: [],
              states: [],
              type: "",
              select: "",
              description: ""
            }
          ],
          count: 2
        }
      }
    })
  );
  containerDetailFn = () => this.#containerDetailSignal();
  getContainerDetails(containerSerial: string): Observable<PiResponse<ContainerDetails, unknown>> {
    throw new Error("Method not implemented.");
  }
}
export class MockOverflowService implements OverflowServiceInterface {
  private _overflow = false;
  setWidthOverflow(value: boolean) {
    this._overflow = value;
  }
  isWidthOverflowing(selector: string, threshold: number): boolean {
    return this._overflow;
  }
  isHeightOverflowing(args: { selector: string; threshold?: number; thresholdSelector?: string }): boolean {
    return this._overflow;
  }
  getOverflowThreshold(): number {
    return 1920;
  }
}

function makeTokenDetailResponse(tokentype: TokenTypeOption): PiResponse<Tokens> {
  return {
    id: 0,
    jsonrpc: "2.0",
    signature: "",
    time: Date.now(),
    version: "1.0",
    versionnumber: "1.0",
    detail: {},
    result: {
      status: true,
      value: {
        count: 1,
        current: 1,
        tokens: [
          {
            tokentype,
            active: true,
            revoked: false,
            container_serial: "",
            realms: [],
            count: 0,
            count_window: 0,
            description: "",
            failcount: 0,
            id: 0,
            info: {},
            locked: false,
            maxfail: 0,
            otplen: 0,
            resolver: "",
            rollout_state: "",
            serial: "X",
            sync_window: 0,
            tokengroup: [],
            user_id: "",
            user_realm: "",
            username: ""
          }
        ]
      }
    }
  };
}

export class MockTokenService implements TokenServiceInterface {
  bulkDeleteWithConfirmDialog(serialList: TokenDetails[], dialog: any, afterDelete?: () => void): void {
    throw new Error("Method not implemented.");
  }
  importTokens(fileName: string, params: Record<string, any>): Observable<PiResponse<TokenImportResult>> {
    throw new Error("Method not implemented.");
  }
  tokenFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  clearFilter(): void {
    throw new Error("Method not implemented.");
  }
  handleFilterInput($event: Event): void {
    throw new Error("Method not implemented.");
  }
  hiddenApiFilter: string[] = [];
  stopPolling$: Subject<void> = new Subject<void>();
  tokenBaseUrl: string = "mockEnvironment.proxyUrl + '/token'";
  eventPageSize = 10;
  tokenSerial = signal("");
  selectedTokenType: WritableSignal<TokenType> = signal({
    key: "hotp",
    name: "HOTP",
    info: "",
    text: "HMAC-based One-Time Password"
  });
  showOnlyTokenNotInContainer = signal(false);

  tokenDetailResource = new MockHttpResourceRef<PiResponse<Tokens>>(makeTokenDetailResponse("hotp"));
  tokenTypesResource: HttpResourceRef<PiResponse<{}, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue({})
  );
  tokenTypeOptions: WritableSignal<TokenType[]> = signal<TokenType[]>([
    {
      key: "hotp",
      name: "HOTP",
      info: "",
      text: "HMAC-based One-Time Password"
    },
    {
      key: "totp",
      name: "TOTP",
      info: "",
      text: "Time-based One-Time Password"
    },
    {
      key: "push",
      name: "PUSH",
      info: "",
      text: "Push Notification"
    }
  ]);
  pageSize = signal(10);
  tokenIsActive: WritableSignal<boolean> = signal(true);
  tokenIsRevoked: WritableSignal<boolean> = signal(false);
  defaultSizeOptions: number[] = [10, 25, 50, 100];
  apiFilter: string[] = [];
  advancedApiFilter: string[] = [];
  sort: WritableSignal<Sort> = signal({ active: "serial", direction: "asc" });
  pageIndex = signal(0);
  filterParams: Signal<Record<string, string>> = signal({});
  tokenResource = new MockHttpResourceRef(
    MockPiResponse.fromValue<Tokens>({
      count: 0,
      current: 0,
      tokens: []
    })
  );
  tokenSelection: WritableSignal<TokenDetails[]> = signal<TokenDetails[]>([]);
  toggleActive = jest.fn().mockReturnValue(of({}));
  resetFailCount = jest.fn().mockReturnValue(of(null));
  saveTokenDetail = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<boolean>(true)));
  getSerial(otp: string, params: HttpParams): Observable<PiResponse<{ count: number; serial?: string }, unknown>> {
    throw new Error("Method not implemented.");
  }
  resyncOTPToken = jest.fn().mockReturnValue(of(null));
  setTokenInfos(tokenSerial: string, infos: any): Observable<PiResponse<boolean, unknown>[]> {
    throw new Error("Method not implemented.");
  }
  deleteToken(tokenSerial: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  bulkDeleteTokens(selectedTokens: TokenDetails[]): Observable<PiResponse<BulkResult, any>> {
    throw new Error("Method not implemented.");
  }
  revokeToken(tokenSerial: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }
  deleteInfo(tokenSerial: string, infoKey: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }
  unassignUserFromAll(tokenSerials: string[]): Observable<PiResponse<boolean, unknown>[]> {
    throw new Error("Method not implemented.");
  }
  unassignUser = jest.fn().mockReturnValue(of(null));
  bulkUnassignTokens(tokenDetails: TokenDetails[]): Observable<PiResponse<BulkResult, any>> {
    throw new Error("Method not implemented.");
  }
  assignUserToAll(args: {
    tokenSerials: string[];
    username: string;
    realm: string;
    pin?: string;
  }): Observable<PiResponse<boolean, unknown>[]> {
    throw new Error("Method not implemented.");
  }
  assignUser = jest.fn().mockReturnValue(of(null));
  setPin(tokenSerial: string, userPin: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }
  setRandomPin(tokenSerial: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }
  getTokenDetails = jest.fn().mockReturnValue(of({}));
  enrollToken<T extends TokenEnrollmentData, R extends EnrollmentResponse>(args: {
    data: T;
    mapper: TokenApiPayloadMapper<T>;
  }): Observable<R> {
    throw new Error("Method not implemented.");
  }
  lostToken(tokenSerial: string): Observable<LostTokenResponse> {
    throw new Error("Method not implemented.");
  }
  stopPolling(): void {
    throw new Error("Method not implemented.");
  }
  pollTokenRolloutState(args: { tokenSerial: string; initDelay: number }): Observable<PiResponse<Tokens>> {
    throw new Error("Method not implemented.");
  }
  setTokenRealm(tokenSerial: string, value: string[]): Observable<PiResponse<boolean, unknown>> {
    throw new Error("Method not implemented.");
  }
  getTokengroups(): Observable<PiResponse<TokenGroups, unknown>> {
    throw new Error("Method not implemented.");
  }
  setTokengroup(tokenSerial: string, value: string | string[]): Observable<Object> {
    throw new Error("Method not implemented.");
  }
  deleteTokens(tokenSerials: string[]): Observable<Object[]> {
    throw new Error("Method not implemented.");
  }
}
export class MockMachineService implements MachineServiceInterface {
  baseUrl: string = "environment.mockProxyUrl + '/machine/'";
  filterValue: WritableSignal<Record<string, string>> = signal({});
  sshApiFilter: string[] = [];
  sshAdvancedApiFilter: string[] = [];
  offlineApiFilter: string[] = [];
  offlineAdvancedApiFilter: string[] = [];
  machines: WritableSignal<Machines> = signal<Machines>([]);
  tokenApplications: WritableSignal<TokenApplication[]> = signal([]);
  selectedApplicationType = signal<"ssh" | "offline">("ssh");
  pageSize = signal(10);
  machineFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  filterParams = computed(() => {
    let allowedKeywords =
      this.selectedApplicationType() === "ssh"
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
      if (["serial"].includes(key)) {
        params[key] = `*${value}*`;
      }
      if (["hostname", "machineid", "resolver"].includes(key)) {
        params[key] = value;
      }
      if (this.selectedApplicationType() === "ssh" && ["service_id"].includes(key)) {
        params[key] = `*${value}*`;
      }
      if (this.selectedApplicationType() === "offline" && ["count", "rounds"].includes(key)) {
        params[key] = value;
      }
    });
    return params;
  });
  sort: WritableSignal<Sort> = signal({ active: "", direction: "" });
  pageIndex = signal(0);
  machinesResource = new MockHttpResourceRef(MockPiResponse.fromValue<Machines>([]));
  tokenApplicationResource: HttpResourceRef<PiResponse<TokenApplication[], undefined> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue([]));

  deleteAssignMachineToToken() {
    return of({} as any);
  }

  postAssignMachineToToken(args: {
    service_id?: string;
    user?: string;
    serial: string;
    application: "ssh" | "offline";
    machineid: number;
    resolver: string;
    count?: number;
    rounds?: number;
  }): Observable<any> {
    return of({} as any);
  }
  postTokenOption = jest.fn().mockReturnValue(of({} as any));
  getAuthItem = jest.fn().mockReturnValue(
    of({
      result: {
        value: { serial: "", machineid: "", resolver: "" }
      }
    })
  );
  postToken = jest.fn().mockReturnValue(of({} as any));
  getMachine = jest.fn().mockReturnValue(
    of({
      result: {
        value: {
          machines: [
            {
              hostname: "localhost",
              machineid: "machine1",
              resolver: "resolver1",
              serial: "serial1",
              type: "ssh",
              applications: []
            }
          ],
          count: 1
        }
      }
    })
  );
  deleteToken = jest.fn().mockReturnValue(of({} as any));
  deleteTokenMtid = jest.fn().mockReturnValue(of({} as any));
  onPageEvent = jest.fn();
  onSortEvent = jest.fn();
  handleFilterInput($event: Event): void {
    throw new Error("Method not implemented.");
  }
  clearFilter(): void {
    throw new Error("Method not implemented.");
  }
}
export class MockTableUtilsService implements TableUtilsServiceInterface {
  pageSizeOptions: WritableSignal<number[]> = signal([5, 10, 25, 50]);
  emptyDataSource = jest.fn().mockImplementation((_pageSize: number, _columns: { key: string; label: string }[]) => {
    const dataSource = new MatTableDataSource<TokenApplication>([]);
    (dataSource as any).isEmpty = true;
    return dataSource;
  });
  toggleKeywordInFilter = jest.fn();
  public toggleBooleanInFilter = jest.fn();
  isLink = jest.fn().mockReturnValue(false);
  getClassForColumn = jest.fn();
  getTooltipForColumn = jest.fn();
  getDisplayText = jest.fn();
  getSpanClassForKey = jest.fn().mockReturnValue("");
  getDivClassForKey = jest.fn().mockReturnValue("");
  getClassForColumnKey = jest.fn();
  getChildClassForColumnKey = jest.fn().mockReturnValue("");
  getDisplayTextForKeyAndRevoked = jest.fn().mockReturnValue("");
  getTdClassForKey = jest.fn().mockReturnValue("");
  getSpanClassForState = jest.fn().mockReturnValue("");
  getDisplayTextForState = jest.fn().mockReturnValue("");
  handleColumnClick = jest.fn();
}
export class MockAuditService implements AuditServiceInterface {
  sort: WritableSignal<Sort> = signal({ active: "time", direction: "desc" });
  apiFilter = ["user", "success"];
  advancedApiFilter = ["machineid", "resolver"];
  auditFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  filterParams: Signal<Record<string, string>> = signal({});
  pageSize = linkedSignal({
    source: this.auditFilter,
    computation: () => 10
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.auditFilter(),
      pageSize: this.pageSize()
    }),
    computation: () => 0
  });
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue<Audit>({
      auditcolumns: [],
      auditdata: [],
      count: 0,
      current: 0
    })
  );
  clearFilter = jest.fn().mockImplementation(() => {
    this.auditFilter.set(new FilterValue());
  });
  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    const inputElement = $event.target as HTMLInputElement;
    this.auditFilter.set(new FilterValue({ value: inputElement.value }));
  });
}
export class MockLocalService implements LocalServiceInterface {
  private data: Record<string, string> = {};
  key: string = "mockLocalServiceKey";
  saveData = jest.fn().mockImplementation((key: string, value: string) => {
    this.data[key] = value;
  });
  getData = jest.fn().mockImplementation((key: string) => {
    const dataValue = this.data[key];
    if (dataValue === undefined) {
      console.warn(`MockLocalService: No data found for key: ${key}`);
      return "";
    }
    return dataValue;
  });
  removeData = jest.fn().mockImplementation((key: string) => {
    if (this.data[key] !== undefined) {
      delete this.data[key];
    } else {
      console.warn(`MockLocalService: No data found for key: ${key}`);
    }
  });
}

export class MockSessionTimerService {
  remainingTime = signal(300);
}

export class MockChallengesService {
  challengesResource = { reload: jest.fn() };
}

export class MockDialogService {
  private _firstStepClosed$ = new Subject<any>();
  private _lastStepClosed$ = new Subject<any>();
  isTokenEnrollmentFirstStepDialogOpen = false;
  openTokenEnrollmentFirstStepDialog = jest.fn((_args: { data: { enrollmentResponse: any } }) => {
    this.isTokenEnrollmentFirstStepDialogOpen = true;

    const ref = {
      close: jest.fn((result?: any) => {
        this.isTokenEnrollmentFirstStepDialogOpen = false;
        this._firstStepClosed$.next(result);
        this._firstStepClosed$.complete();
        this._firstStepClosed$ = new Subject<any>();
      }),
      afterClosed: () => this._firstStepClosed$.asObservable()
    } as any;

    return ref;
  });

  closeTokenEnrollmentFirstStepDialog = jest.fn(() => {
    if (this.isTokenEnrollmentFirstStepDialogOpen) {
      this.isTokenEnrollmentFirstStepDialogOpen = false;
      this._firstStepClosed$.next(undefined);
      this._firstStepClosed$.complete();
      this._firstStepClosed$ = new Subject<any>();
    }
  });

  openTokenEnrollmentLastStepDialog = jest.fn((_args: { data: TokenEnrollmentLastStepDialogData }) => {
    const ref = {
      close: jest.fn((result?: any) => {
        this._lastStepClosed$.next(result);
        this._lastStepClosed$.complete();
        this._lastStepClosed$ = new Subject<any>();
      }),
      afterClosed: () => this._lastStepClosed$.asObservable()
    } as any;

    return ref;
  });

  closeTokenEnrollmentLastStepDialog = jest.fn(() => {
    this._lastStepClosed$.next(undefined);
    this._lastStepClosed$.complete();
    this._lastStepClosed$ = new Subject<any>();
  });
}

export class MockLoadingService {
  addLoading = jest.fn();
  removeLoading = jest.fn();
}

type TestApplicationsShape = {
  ssh: {
    options: {
      sshkey: {
        service_id: { value: string[] };
      };
    };
  };
};

export class MockApplicationService {
  applications: WritableSignal<TestApplicationsShape> = signal({
    ssh: {
      options: {
        sshkey: {
          service_id: { value: ["svc-1", "svc-2"] }
        }
      }
    }
  });
}

export class MockVersioningService {
  version = { set: jest.fn() } as any;
}
