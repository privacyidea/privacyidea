import { HttpClient, HttpHeaders, HttpParams, HttpProgressEvent, HttpResourceRef } from "@angular/common/http";
import { computed, linkedSignal, Resource, ResourceStatus, Signal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { MatTableDataSource } from "@angular/material/table";
import { Router } from "@angular/router";
import { Observable, of, Subject, Subscription } from "rxjs";
import { PiResponse } from "../app/app.component";
import { BEARER_TOKEN_STORAGE_KEY } from "../app/core/constants";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../app/mappers/token-api-payload/_token-api-payload.mapper";
import { Audit, AuditServiceInterface } from "../app/services/audit/audit.service";
import {
  AuthData,
  AuthDetail,
  AuthResponse,
  AuthRole,
  AuthServiceInterface,
  JwtData
} from "../app/services/auth/auth.service";
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
import { LocalServiceInterface } from "../app/services/local/local.service";
import { Machines, MachineServiceInterface, TokenApplication } from "../app/services/machine/machine.service";
import { NotificationServiceInterface } from "../app/services/notification/notification.service";
import { OverflowServiceInterface } from "../app/services/overflow/overflow.service";
import { Realm, Realms, RealmServiceInterface } from "../app/services/realm/realm.service";
import { FilterPair, TableUtilsServiceInterface } from "../app/services/table-utils/table-utils.service";
import {
  BatchResult,
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

export class MockAuthService implements AuthServiceInterface {
  readonly authUrl = "environmentMock.proxyUrl + '/auth'";
  jwtData: WritableSignal<JwtData | null> = signal({
    username: "",
    realm: "",
    nonce: "",
    role: "admin",
    authtype: "cookie",
    exp: 0,
    rights: []
  });
  jwtNonce: WritableSignal<string> = signal(this.jwtData()?.nonce || "");
  authtype: Signal<"cookie" | "none"> = signal("cookie");
  jwtExpDate: Signal<Date | null> = computed(() => {
    const exp = this.jwtData()?.exp;
    return exp ? new Date(exp * 1000) : null;
  });
  authData = signal(MockAuthService.MOCK_AUTH_DATA);
  authenticationAccepted: () => boolean = () => {
    return this.isAuthenticated() && this.role() !== "";
  };
  isAuthenticated: WritableSignal<boolean> = signal(false);

  public getHeaders(): HttpHeaders {
    return new HttpHeaders({
      "PI-Authorization": this.localService.getData(BEARER_TOKEN_STORAGE_KEY) || ""
    });
  }

  logLevel: () => number = () => {
    return this.authData().log_level;
  };
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
  policyTemplateUrl: () => string = () => {
    return this.authData().policy_template_url;
  };
  defaultTokentype: () => string = () => {
    return this.authData().default_tokentype;
  };
  defaultContainerType: () => string = () => {
    return this.authData().default_container_type;
  };
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
  logout = jest.fn().mockImplementation(() => {
    this.isAuthenticated.set(false);
    this.role.set("");
    this.username.set("");
    this.realm.set("");
  });
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
  isAuthenticatedUser = jest.fn().mockReturnValue(this.isAuthenticated() && this.role() === "user");

  constructor(
    readonly http: HttpClient = new HttpClient({} as any),
    readonly localService: LocalServiceInterface = new MockLocalService(),
    readonly notificationService: NotificationServiceInterface = new MockNotificationService(),
    readonly versioningService: VersioningService = new VersioningService()
  ) {}
}

export class MockUserService implements UserServiceInterface {
  usersOfRealmResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  selectedUserRealm = signal("");
  selectedUser = signal<UserData | null>(null);
  userFilter = signal("");
  userNameFilter = signal("");
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
  filteredUsernames: Signal<string[]> = signal([]);
  filteredUsers = signal([]);
  filterValue: WritableSignal<Record<string, string>> = signal({});
  pageIndex: WritableSignal<number> = signal(0);
  pageSize: WritableSignal<number> = signal(10);
  apiFilter: string[] = [];
  advancedApiFilter: string[] = [];

  displayUser(user: UserData | string): string {
    throw new Error("Method not implemented.");
  }

  selectedUsername = signal("");
  setDefaultRealm = jest.fn();

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
  realmResource = new MockHttpResourceRef(MockPiResponse.fromValue<Realms>(new Map<string, Realm>()));
  realmOptions = signal(["realm1", "realm2"]);
  defaultRealmResource = new MockHttpResourceRef(MockPiResponse.fromValue<Realms>(new Map<string, Realm>()));
  defaultRealm = signal("realm1");
}

export class MockContentService implements ContentServiceInterface {
  router: Router = {
    url: "/home",
    events: of({} as any)
  } as any;
  routeUrl: Signal<string> = signal("/home");
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
  states = signal<string[]>([]);
  containerSerial = signal("CONT-1");
  selectedContainer = signal("");
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
  containerDetail = this.#containerDetailSignal;
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

  containerBelongsToUser = jest.fn().mockReturnValue(true);

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

export class MockTokenService implements TokenServiceInterface {
  hiddenApiFilter: string[] = [];
  stopPolling$: Subject<void> = new Subject<void>();
  tokenBaseUrl: string = "mockEnvironment.proxyUrl + '/token'";
  eventPageSize = 10;
  tokenSerial = signal("");
  selectedTokenType: WritableSignal<TokenType> = signal({
    key: "hotp",
    info: "",
    text: "HMAC-based One-Time Password"
  });
  showOnlyTokenNotInContainer = signal(false);
  filterValue = signal<Record<string, string>>({});
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
  tokenTypesResource: HttpResourceRef<PiResponse<{}, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue({})
  );
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

  batchDeleteTokens(selectedTokens: TokenDetails[]): Observable<PiResponse<BatchResult, any>> {
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

  batchUnassignTokens(tokenDetails: TokenDetails[]): Observable<PiResponse<BatchResult, any>> {
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

  getRealms = jest.fn().mockReturnValue(of({ result: { value: [] } }));
  getTokenData = this.getTokenDetails;

  deleteTokens(tokenSerials: string[]): Observable<Object[]> {
    throw new Error("Method not implemented.");
  }
}

export class MockMachineService implements MachineServiceInterface {
  baseUrl: string = "environment.mockProxyUrl + '/machine/'";
  sshApiFilter: string[] = [];
  sshAdvancedApiFilter: string[] = [];
  offlineApiFilter: string[] = [];
  offlineAdvancedApiFilter: string[] = [];
  machines: WritableSignal<Machines> = signal<Machines>([]);
  tokenApplications: WritableSignal<TokenApplication[]> = signal([]);
  selectedApplicationType = signal<"ssh" | "offline">("ssh");
  pageSize = signal(10);
  filterValue: WritableSignal<Record<string, string>> = signal({});
  filterValueString: WritableSignal<string> = signal("");
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

  constructor(
    public http: HttpClient = new HttpClient({} as any),
    public authService: AuthServiceInterface = new MockAuthService(),
    public tableUtilsService: TableUtilsServiceInterface = new MockTableUtilsService()
  ) {}
}

export class MockTableUtilsService implements TableUtilsServiceInterface {
  pageSizeOptions: WritableSignal<number[]> = signal([5, 10, 25, 50]);
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
  isLink = jest.fn().mockReturnValue(false);
  getClassForColumn = jest.fn();
  getTooltipForColumn = jest.fn();
  getDisplayText = jest.fn();

  getSpanClassForKey(args: { key: string; value?: any; maxfail?: any }): string {
    throw new Error("Mock method not implemented.");
  }

  getDivClassForKey(key: string): "" | "details-scrollable-container" | "details-value" {
    throw new Error("Mock method not implemented.");
  }

  getClassForColumnKey = jest.fn();

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

  handleColumnClick = jest.fn();
}

export class MockAuditService implements AuditServiceInterface {
  sort: WritableSignal<Sort> = signal({ active: "time", direction: "desc" });
  apiFilter = ["user", "success"];
  advancedApiFilter = ["machineid", "resolver"];
  filterValue = signal<Record<string, string>>({});
  filterParams: Signal<Record<string, string>> = signal({});
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
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue<Audit>({
      auditcolumns: [],
      auditdata: [],
      count: 0,
      current: 0
    })
  );
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
