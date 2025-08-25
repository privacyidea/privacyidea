import { HttpClient, HttpHeaders, HttpParams, HttpProgressEvent, HttpResourceRef } from "@angular/common/http";
import { computed, linkedSignal, Resource, ResourceStatus, Signal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { MatTableDataSource } from "@angular/material/table";
import { Router } from "@angular/router";
import { Observable, of, Subject, Subscription } from "rxjs";
import { PiResponse } from "../app/app.component";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../app/mappers/token-api-payload/_token-api-payload.mapper";
import { Audit, AuditServiceInterface } from "../app/services/audit/audit.service";
import { AuthData, AuthDetail, AuthResponse, AuthRole, AuthServiceInterface } from "../app/services/auth/auth.service";
import {
  ContainerDetailData,
  ContainerDetails,
  ContainerRegisterData,
  ContainerServiceInterface,
  ContainerTemplate,
  ContainerType,
  ContainerTypes
} from "../app/services/container/container.service";
import { ContentServiceInterface } from "../app/services/content/content.service";
import { LocalService, LocalServiceInterface } from "../app/services/local/local.service";
import { Machines, MachineServiceInterface, TokenApplication } from "../app/services/machine/machine.service";
import { NotificationServiceInterface } from "../app/services/notification/notification.service";
import { OverflowServiceInterface } from "../app/services/overflow/overflow.service";
import { Realm, Realms, RealmServiceInterface } from "../app/services/realm/realm.service";
import { FilterPair, TableUtilsService } from "../app/services/table-utils/table-utils.service";
import {
  LostTokenResponse,
  TokenDetails,
  TokenGroups,
  Tokens,
  TokenServiceInterface,
  TokenType
} from "../app/services/token/token.service";
import { UserData, UserServiceInterface } from "../app/services/user/user.service";
import { ValidateCheckResponse, ValidateServiceInterface } from "../app/services/validate/validate.service";
import { VersioningService } from "../app/services/version/version.service";

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
  versionnumber = "";
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
    enabled: false
  };
}

export class MockAuthDetail implements AuthDetail {
  username = "";
}

export class MockHttpResourceRef<T> implements HttpResourceRef<T> {
  value: WritableSignal<T>;
  reload = jest.fn();
  error = signal<Error | null>(null);
  headers: Signal<HttpHeaders | undefined> = signal(undefined);
  statusCode: Signal<number | undefined> = signal(undefined);
  progress: Signal<HttpProgressEvent | undefined> = signal(undefined);
  status: Signal<ResourceStatus> = signal(ResourceStatus.Resolved);
  isLoading: Signal<boolean> = signal(false);

  constructor(initial: T) {
    this.value = signal(initial) as WritableSignal<T>;
  }

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
      isLoading: signal(false)
    };
  }
}

export class MockPiResponse<Value, Detail = unknown> implements PiResponse<Value, Detail> {
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
  error?: {
    code: number;
    message: string;
  };

  id: number;
  jsonrpc: string;
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

export class MockAuthService implements AuthServiceInterface {
  readonly authUrl = "environmentMock.proxyUrl + '/auth'";

  static MOCK_AUTH_DATA: AuthData = {
    log_level: 0,
    menus: ["token_overview", "token_self-service_menu", "container_overview"],
    realm: "default",
    rights: [],
    role: "admin",
    token: "",
    username: "alice",
    logout_time: 3600,
    audit_page_size: 10,
    token_page_size: 10,
    user_page_size: 10,
    policy_template_url: "",
    default_tokentype: "",
    default_container_type: "",
    user_details: false,
    token_wizard: false,
    token_wizard_2nd: false,
    admin_dashboard: false,
    dialog_no_token: false,
    search_on_enter: false,
    timeout_action: "",
    token_rollover: null,
    hide_welcome: false,
    hide_buttons: false,
    deletion_confirmation: false,
    show_seed: false,
    show_node: "",
    subscription_status: 0,
    subscription_status_push: 0,
    qr_image_android: null,
    qr_image_ios: null,
    qr_image_custom: null,
    logout_redirect_url: "",
    require_description: [],
    rss_age: 0,
    container_wizard: {
      enabled: false
    }
  };

  authData = signal(MockAuthService.MOCK_AUTH_DATA);

  isAuthenticated: WritableSignal<boolean> = signal(true);
  menus: WritableSignal<string[]> = signal(MockAuthService.MOCK_AUTH_DATA.menus);
  realm: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.realm);
  rights: WritableSignal<string[]> = signal(MockAuthService.MOCK_AUTH_DATA.rights);
  role: WritableSignal<AuthRole> = signal(MockAuthService.MOCK_AUTH_DATA.role);
  token: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.token);
  username: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.username);
  logoutTimeSeconds: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.logout_time);
  auditPageSize: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.audit_page_size);
  tokenPageSize: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.token_page_size);
  userPageSize: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.user_page_size);
  userDetails: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.user_details);
  tokenWizard: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.token_wizard);
  tokenWizard2nd: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.token_wizard_2nd);
  adminDashboard: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.admin_dashboard);
  dialogNoToken: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.dialog_no_token);
  searchOnEnter: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.search_on_enter);
  timeoutAction: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.timeout_action);
  tokenRollover: WritableSignal<any> = signal(MockAuthService.MOCK_AUTH_DATA.token_rollover);
  hideWelcome: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.hide_welcome);
  hideButtons: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.hide_buttons);
  deletionConfirmation: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.deletion_confirmation);
  showSeed: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.show_seed);
  showNode: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.show_node);
  subscriptionStatus: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.subscription_status);
  subscriptionStatusPush: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.subscription_status_push);
  qrImageAndroid: WritableSignal<string | null> = signal(MockAuthService.MOCK_AUTH_DATA.qr_image_android);
  qrImageIOS: WritableSignal<string | null> = signal(MockAuthService.MOCK_AUTH_DATA.qr_image_ios);
  qrImageCustom: WritableSignal<string | null> = signal(MockAuthService.MOCK_AUTH_DATA.qr_image_custom);
  logoutRedirectUrl: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.logout_redirect_url);
  requireDescription: WritableSignal<string[]> = signal(MockAuthService.MOCK_AUTH_DATA.require_description);
  rssAge: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.rss_age);
  containerWizard: WritableSignal<{ enabled: boolean }> = signal(MockAuthService.MOCK_AUTH_DATA.container_wizard);

  isSelfServiceUser: Signal<boolean> = signal(
    this.role() === "user" && this.menus().includes("token_self-service_menu")
  );
  authenticate = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail())));
  acceptAuthentication = jest.fn().mockImplementation(() => {
    this.isAuthenticated.set(true);
    this.role.set("admin");
    this.username.set("alice");
    this.realm.set("default");
  });

  deauthenticate = jest.fn().mockImplementation(() => {
    this.isAuthenticated.set(false);
    this.role.set("");
    this.username.set("");
    this.realm.set("");
  });

  isAuthenticatedUser = jest.fn().mockReturnValue(this.isAuthenticated() && this.role() === "user");

  constructor(
    readonly http: HttpClient = new HttpClient({} as any),
    readonly notificationService: NotificationServiceInterface = new MockNotificationService(),
    readonly versioningService: VersioningService = new VersioningService()
  ) {}
}

export class MockUserService implements UserServiceInterface {
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
  usersOfRealmResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  filteredUsernames: Signal<string[]> = signal([]);
  selectedUserRealm = signal("");
  selectedUsername = signal("");
  userFilter = signal("");
  userNameFilter = signal("");
  setDefaultRealm = jest.fn();
  filteredUsers = signal([]);
  selectedUser = signal<UserData | null>(null);

  displayUser(user: UserData | string): string {
    throw new Error("Method not implemented.");
  }

  resetUserSelection() {
    this.userFilter.set("");
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
}

export class MockRealmService implements RealmServiceInterface {
  realmResource = new MockHttpResourceRef(MockPiResponse.fromValue<Realms>(new Map<string, Realm>()));
  defaultRealmResource = new MockHttpResourceRef(MockPiResponse.fromValue<Realms>(new Map<string, Realm>()));

  realmOptions = signal(["realm1", "realm2"]);
  defaultRealm = signal("realm1");
  selectedRealms = signal<string[]>([]);
}

export class MockContentService implements ContentServiceInterface {
  router: Router = {
    url: "/home",
    events: of({} as any)
  } as any;
  routeUrl: Signal<string> = signal("/home");
  previousUrl: Signal<string> = signal("/home");
  tokenSerial: WritableSignal<string> = signal("");
  containerSerial: WritableSignal<string> = signal("");

  tokenSelected = jest.fn().mockImplementation((serial: string) => {
    this.tokenSerial.set(serial);
  });

  containerSelected = jest.fn().mockImplementation((serial: string) => {
    this.containerSerial.set(serial);
  });
  isProgrammaticTabChange = signal(false);

  constructor(public authService: MockAuthService = new MockAuthService()) {}
}

export class MockContainerService implements ContainerServiceInterface {
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
  sort: WritableSignal<Sort> = signal({ active: "serial", direction: "asc" });
  filterValue: WritableSignal<Record<string, string>> = signal({});
  filterParams: Signal<Record<string, string>> = computed(() =>
    Object.fromEntries(
      Object.entries(this.filterValue()).filter(([key]) => [...this.apiFilter, ...this.advancedApiFilter].includes(key))
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
    const filter = this.filterValue();
    return options.filter((option) => {
      return Object.keys(filter).every((key) => {
        return option.includes(filter[key]);
      });
    });
  });
  containerSelection: WritableSignal<ContainerDetailData[]> = signal([]);
  containerTypesResource: HttpResourceRef<PiResponse<ContainerTypes, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue<ContainerTypes>(new Map())
  );
  containerTypeOptions: Signal<ContainerType[]> = computed(() => {
    const types = this.containerTypesResource.value()?.result?.value;
    return types ? Object.values(types) : [];
  });
  selectedContainerType: WritableSignal<ContainerType> = signal({
    containerType: "generic",
    description: "",
    token_types: []
  });
  templatesResource: HttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined> =
    new MockHttpResourceRef(
      MockPiResponse.fromValue<{ templates: ContainerTemplate[] }>({
        templates: []
      })
    );
  templates: WritableSignal<ContainerTemplate[]> = signal([]);
  toggleActive = jest.fn().mockReturnValue(of({}));
  setContainerInfos = jest.fn().mockReturnValue(of({}));
  deleteInfo = jest.fn().mockReturnValue(of({}));
  deleteContainer = jest.fn().mockReturnValue(of({}));
  states = signal<string[]>([]);
  containerSerial = signal("CONT-1");
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
  unassignContainer = jest.fn().mockReturnValue(of(null));
  assignContainer = jest.fn().mockReturnValue(of(null));
  containerDetail = this.#containerDetailSignal;
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
  selectedContainer = signal("");
  addTokenToContainer = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  unassignUser = jest.fn().mockReturnValue(of(null));
  setContainerRealm = jest.fn().mockReturnValue(of(null));
  setContainerDescription = jest.fn().mockReturnValue(of(null));
  deleteAllTokens = jest.fn().mockReturnValue(of(null));
  toggleAll = jest.fn().mockReturnValue(of(null));
  removeAll = jest.fn().mockReturnValue(of(null));
  removeTokenFromContainer = jest.fn().mockReturnValue(of(null));

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

  getContainerDetails(containerSerial: string): Observable<PiResponse<ContainerDetails, unknown>> {
    throw new Error("Method not implemented.");
  }

  pollContainerRolloutState(
    containerSerial: string,
    startTime: number
  ): Observable<PiResponse<ContainerDetails, unknown>> {
    throw new Error("Method not implemented.");
  }

  containerDetailFn = () => this.#containerDetailSignal();
}

export class MockOverflowService implements OverflowServiceInterface {
  private _overflow = false;

  getOverflowThreshold(): number {
    return 1920;
  }

  setWidthOverflow(value: boolean) {
    this._overflow = value;
  }

  isWidthOverflowing(selector: string, threshold: number): boolean {
    return this._overflow;
  }

  isHeightOverflowing(args: { selector: string; threshold?: number; thresholdSelector?: string }): boolean {
    return this._overflow;
  }
}

export class MockTokenService implements TokenServiceInterface {
  apiFilter: string[] = [];
  advancedApiFilter: string[] = [];
  hiddenApiFilter: string[] = [];
  tokenBaseUrl: string = "mockEnvironment.proxyUrl + '/token'";
  stopPolling$: Subject<void> = new Subject<void>();
  tokenIsActive: WritableSignal<boolean> = signal(true);
  tokenIsRevoked: WritableSignal<boolean> = signal(false);
  tokenTypesResource: HttpResourceRef<PiResponse<{}, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue({})
  );
  sort: WritableSignal<Sort> = signal({ active: "serial", direction: "asc" });

  filterParams: Signal<Record<string, string>> = signal({});

  saveTokenDetail = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<boolean>(true)));
  showOnlyTokenNotInContainer = signal(false);
  tokenDetailResource = new MockHttpResourceRef(
    MockPiResponse.fromValue<Tokens>({
      count: 1,
      current: 1,
      tokens: [
        {
          tokentype: "hotp",
          active: true,
          revoked: false,
          container_serial: "CONT-1",
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
          serial: "",
          sync_window: 0,
          tokengroup: [],
          user_id: "",
          user_realm: "",
          username: ""
        }
      ]
    })
  );
  tokenSerial = signal("");
  filterValue = signal<Record<string, string>>({});
  pageIndex = signal(0);
  pageSize = signal(10);
  tokenTypeOptions: WritableSignal<TokenType[]> = signal<TokenType[]>([
    {
      key: "hotp",
      info: "",
      text: "HMAC-based One-Time Password"
    },
    {
      key: "totp",
      info: "",
      text: "Time-based One-Time Password"
    },
    {
      key: "push",
      info: "",
      text: "Push Notification"
    }
  ]);
  tokenSelection: WritableSignal<TokenDetails[]> = signal<TokenDetails[]>([]);
  defaultSizeOptions: number[] = [10, 25, 50, 100];
  eventPageSize = 10;
  selectedTokenType: WritableSignal<TokenType> = signal({
    key: "hotp",
    info: "",
    text: "HMAC-based One-Time Password"
  });
  tokenResource = new MockHttpResourceRef(
    MockPiResponse.fromValue<Tokens>({
      count: 0,
      current: 0,
      tokens: []
    })
  );
  getTokenDetails = jest.fn().mockReturnValue(of({}));
  getRealms = jest.fn().mockReturnValue(of({ result: { value: [] } }));
  resetFailCount = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  unassignUser = jest.fn().mockReturnValue(of(null));
  toggleActive = jest.fn().mockReturnValue(of({}));
  getTokenData = this.getTokenDetails;

  setTokenInfos(tokenSerial: string, infos: any): Observable<PiResponse<boolean, unknown>[]> {
    throw new Error("Method not implemented.");
  }

  deleteToken(tokenSerial: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  deleteTokens(tokenSerials: string[]): Observable<Object[]> {
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

  assignUserToAll(args: {
    tokenSerials: string[];
    username: string;
    realm: string;
    pin?: string;
  }): Observable<PiResponse<boolean, unknown>[]> {
    throw new Error("Method not implemented.");
  }

  setPin(tokenSerial: string, userPin: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  setRandomPin(tokenSerial: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  resyncOTPToken(tokenSerial: string, fristOTPValue: string, secondOTPValue: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  setTokenRealm(tokenSerial: string, value: string[]): Observable<PiResponse<boolean, unknown>> {
    throw new Error("Method not implemented.");
  }

  setTokengroup(tokenSerial: string, value: string | string[]): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  lostToken(tokenSerial: string): Observable<LostTokenResponse> {
    throw new Error("Method not implemented.");
  }

  enrollToken<T extends TokenEnrollmentData, R extends EnrollmentResponse>(args: {
    data: T;
    mapper: TokenApiPayloadMapper<T>;
  }): Observable<R> {
    throw new Error("Method not implemented.");
  }

  getTokengroups(): Observable<PiResponse<TokenGroups, unknown>> {
    throw new Error("Method not implemented.");
  }

  getSerial(otp: string, params: HttpParams): Observable<PiResponse<{ count: number; serial?: string }, unknown>> {
    throw new Error("Method not implemented.");
  }

  pollTokenRolloutState(args: { tokenSerial: string; initDelay: number }): Observable<PiResponse<Tokens>> {
    throw new Error("Method not implemented.");
  }

  stopPolling(): void {
    throw new Error("Method not implemented.");
  }
}

export class MockMachineService implements MachineServiceInterface {
  baseUrl: string = "environment.mockProxyUrl + '/machine/'";
  sshApiFilter: string[] = [];
  sshAdvancedApiFilter: string[] = [];
  offlineApiFilter: string[] = [];
  offlineAdvancedApiFilter: string[] = [];
  machinesResource = new MockHttpResourceRef(MockPiResponse.fromValue<Machines>([]));
  machines: WritableSignal<Machines> = signal<Machines>([]);
  filterValue: WritableSignal<Record<string, string>> = signal({});
  filterValueString: WritableSignal<string> = signal("");
  sort: WritableSignal<Sort> = signal({ active: "", direction: "" });
  tokenApplications: WritableSignal<TokenApplication[]> = signal([]);
  tokenApplicationResource: HttpResourceRef<PiResponse<TokenApplication[], undefined> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue([]));

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
  selectedApplicationType = signal<"ssh" | "offline">("ssh");
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
  pageSize = signal(10);
  pageIndex = signal(0);

  constructor(
    public http: HttpClient = new HttpClient({} as any),
    public localService: LocalService = new LocalService(),
    public tableUtilsService: TableUtilsService = new MockTableUtilsService()
  ) {}

  postAssignMachineToToken(args: {
    service_id: string;
    user: string;
    serial: string;
    application: string;
    machineid: string;
    resolver: string;
  }): Observable<any> {
    throw new Error("Mock method not implemented.");
  }
}

export class MockTableUtilsService implements AuthServiceInterface {
  isAuthenticated: () => boolean = jest.fn().mockReturnValue(true);
  username: () => string = jest.fn().mockReturnValue("alice");
  realm: () => string = jest.fn().mockReturnValue("default");
  role: () => AuthRole = jest.fn().mockReturnValue("admin");
  menus: () => string[] = jest
    .fn()
    .mockReturnValue(["token_overview", "token_self-service_menu", "container_overview"]);
  isSelfServiceUser: () => boolean = jest
    .fn()
    .mockReturnValue(this.role() === "user" && this.menus().includes("token_self-service_menu"));
  authenticate: (params: any) => Observable<AuthResponse> = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail())));
  isAuthenticatedUser: () => boolean = jest.fn().mockReturnValue(this.isAuthenticated() && this.role() === "user");
  acceptAuthentication: () => void = jest.fn().mockImplementation(() => {
    this.isAuthenticated = jest.fn().mockReturnValue(true);
    this.role = jest.fn().mockReturnValue("admin");
    this.username = jest.fn().mockReturnValue("alice");
    this.realm = jest.fn().mockReturnValue("default");
  });
  deauthenticate: () => void = jest.fn().mockImplementation(() => {
    this.isAuthenticated = jest.fn().mockReturnValue(false);
    this.role = jest.fn().mockReturnValue("");
    this.username = jest.fn().mockReturnValue("");
    this.realm = jest.fn().mockReturnValue("");
  });
  handleColumnClick = jest.fn();
  getClassForColumnKey = jest.fn();
  isLink = jest.fn().mockReturnValue(false);
  getClassForColumn = jest.fn();
  getDisplayText = jest.fn();
  getTooltipForColumn = jest.fn();
  recordsFromText = jest.fn((filterString: string) => {
    const records: { [key: string]: string } = {};
    filterString.split(" ").forEach((part) => {
      const [key, value] = part.split(": ");
      if (key && value) {
        records[key] = value;
      }
    });
    return records;
  });
  emptyDataSource = jest.fn().mockImplementation((_pageSize: number, _columns: { key: string; label: string }[]) => {
    const dataSource = new MatTableDataSource<TokenApplication>([]);
    (dataSource as any).isEmpty = true;
    return dataSource;
  });

  parseFilterString(
    filterValue: string,
    apiFilter: string[]
  ): { filterPairs: FilterPair[]; remainingFilterText: string } {
    throw new Error("Mock method not implemented.");
  }

  toggleKeywordInFilter(currentValue: string, keyword: string): string {
    throw new Error("Mock method not implemented.");
  }

  public toggleBooleanInFilter(args: { keyword: string; currentValue: string }): string {
    throw new Error("Mock method not implemented.");
  }

  getSpanClassForKey(args: { key: string; value?: any; maxfail?: any }): string {
    throw new Error("Mock method not implemented.");
  }

  getDivClassForKey(key: string): "" | "details-scrollable-container" | "details-value" {
    throw new Error("Mock method not implemented.");
  }

  getChildClassForColumnKey(columnKey: string): string {
    throw new Error("Mock method not implemented.");
  }

  getDisplayTextForKeyAndRevoked(key: string, value: any, revoked: boolean): string {
    throw new Error("Mock method not implemented.");
  }

  getTdClassForKey(key: string): string[] {
    throw new Error("Mock method not implemented.");
  }

  getSpanClassForState(state: string, clickable: boolean): string {
    throw new Error("Mock method not implemented.");
  }

  getDisplayTextForState(state: string): string {
    throw new Error("Mock method not implemented.");
  }
}

export class MockAuditService implements AuditServiceInterface {
  filterParams: Signal<Record<string, string>> = signal({});
  sort: WritableSignal<Sort> = signal({ active: "time", direction: "desc" });
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue<Audit>({
      auditcolumns: [],
      auditdata: [],
      count: 0,
      current: 0
    })
  );
  apiFilter = ["user", "success"];
  advancedApiFilter = ["machineid", "resolver"];

  filterValue = signal<Record<string, string>>({});

  pageSize = linkedSignal({
    source: this.filterValue,
    computation: () => 10
  });

  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize()
    }),
    computation: () => 0
  });
}

export class MockLocalService implements LocalServiceInterface {
  private data: Record<string, string> = {};
  key: string = "mockLocalServiceKey";
  bearerTokenKey: string = "mockBearerTokenKey";
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

  getHeaders = jest.fn().mockReturnValue({ Authorization: "Bearer x" });
}
