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
import { AuthData, AuthDetail, AuthResponse, AuthRole, AuthService, JwtData } from "../app/services/auth/auth.service";
import {
  ContainerDetailData,
  ContainerDetails,
  ContainerRegisterData,
  ContainerService,
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
  Tokens,
  TokenService,
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
import { UserAttributePolicy, UserData, UserServiceInterface } from "../app/services/user/user.service";
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
import { ColumnDef, ColumnKey, TableUtilsServiceInterface } from "../app/services/table-utils/table-utils.service";
import { TokenEnrollmentLastStepDialogData } from "../app/components/token/token-enrollment/token-enrollment-last-step-dialog/token-enrollment-last-step-dialog.component";
import { TokenTypeOption } from "../app/components/token/token.component";

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

export class MockAuthService extends AuthService {
  override readonly notificationService: NotificationServiceInterface = inject(MockNotificationService);
  override readonly authUrl = "environmentMock.proxyUrl + '/auth'";
  override jwtData: WritableSignal<JwtData | null> = signal({
    username: "",
    realm: "",
    nonce: "",
    role: "admin",
    authtype: "cookie",
    exp: 0,
    rights: MockAuthService.MOCK_AUTH_DATA.rights
  });
  override jwtNonce: WritableSignal<string> = signal(this.jwtData()?.nonce || "");
  override authtype: Signal<"cookie" | "none"> = signal("cookie");
  override jwtExpDate: Signal<Date | null> = computed(() => {
    const exp = this.jwtData()?.exp;
    return exp ? new Date(exp * 1000) : null;
  });
  override authData = signal(MockAuthService.MOCK_AUTH_DATA);
  override isAuthenticated: WritableSignal<boolean> = signal(false);
  override menus: WritableSignal<string[]> = signal(MockAuthService.MOCK_AUTH_DATA.menus);
  override realm: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.realm);
  override role: WritableSignal<AuthRole> = signal(MockAuthService.MOCK_AUTH_DATA.role);
  override token: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.token);
  override username: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.username);
  override logoutTimeSeconds: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.logout_time);
  override auditPageSize: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.audit_page_size);
  override tokenPageSize: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.token_page_size);
  override userPageSize: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.user_page_size);
  override userDetails: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.user_details);
  override tokenWizard2nd: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.token_wizard_2nd);
  override adminDashboard: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.admin_dashboard);
  override dialogNoToken: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.dialog_no_token);
  override searchOnEnter: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.search_on_enter);
  override timeoutAction: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.timeout_action);
  override tokenRollover: WritableSignal<any> = signal(MockAuthService.MOCK_AUTH_DATA.token_rollover);
  override hideWelcome: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.hide_welcome);
  override hideButtons: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.hide_buttons);
  override deletionConfirmation: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.deletion_confirmation);
  override showSeed: WritableSignal<boolean> = signal(MockAuthService.MOCK_AUTH_DATA.show_seed);
  override showNode: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.show_node);
  override subscriptionStatus: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.subscription_status);
  override subscriptionStatusPush: WritableSignal<number> = signal(
    MockAuthService.MOCK_AUTH_DATA.subscription_status_push
  );
  override qrImageAndroid: WritableSignal<string | null> = signal(MockAuthService.MOCK_AUTH_DATA.qr_image_android);
  override qrImageIOS: WritableSignal<string | null> = signal(MockAuthService.MOCK_AUTH_DATA.qr_image_ios);
  override qrImageCustom: WritableSignal<string | null> = signal(MockAuthService.MOCK_AUTH_DATA.qr_image_custom);
  override logoutRedirectUrl: WritableSignal<string> = signal(MockAuthService.MOCK_AUTH_DATA.logout_redirect_url);
  override requireDescription: WritableSignal<string[]> = signal(MockAuthService.MOCK_AUTH_DATA.require_description);
  override rssAge: WritableSignal<number> = signal(MockAuthService.MOCK_AUTH_DATA.rss_age);
  override isSelfServiceUser: Signal<boolean> = signal(
    this.role() === "user" && this.menus().includes("token_self-service_menu")
  );
  override authenticate = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail())));
  protected override readonly localService: LocalServiceInterface = inject(MockLocalService);
  static MOCK_AUTH_DATA: AuthData = {
    log_level: 0,
    menus: ["token_overview", "token_self-service_menu", "container_overview"],
    realm: "default",
    rights: [],
    role: "admin",
    token: "Bearer FAKE_TOKEN",
    username: "alice",
    logout_time: 3600,
    audit_page_size: 25,
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
      enabled: false,
      type: "",
      registration: false,
      template: null
    }
  };
  isAuthenticatedUser = jest.fn().mockReturnValue(this.isAuthenticated() && this.role() === "user");
  override getHeaders = jest
    .fn()
    .mockReturnValue(new HttpHeaders({ Authorization: "Bearer FAKE_TOKEN" }));}

export class MockUserService implements UserServiceInterface {
  usersOfRealmResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue([]));
  selectedUsername = signal("");
  setDefaultRealm = jest.fn();  attributePolicy: Signal<UserAttributePolicy> = signal<UserAttributePolicy>({
    delete: ["department", "attr2", "attr1"],
    set: {
      "*": ["2", "1"],
      city: ["*"],
      department: ["sales", "finance"]
    }
  });

  resetUserSelection() {
    this.selectionFilter.set("");
    this.selectedUserRealm.set("");
  }

  deletableAttributes: Signal<string[]> = computed(() => this.attributePolicy().delete ?? []);

  attributeSetMap: Signal<Record<string, string[]>> = computed(() => this.attributePolicy().set ?? {});

  hasWildcardKey: Signal<boolean> = computed(() =>
    Object.prototype.hasOwnProperty.call(this.attributeSetMap(), "*")
  );
  keyOptions: Signal<string[]> = computed(() =>
    Object.keys(this.attributeSetMap()).filter((k) => k !== "*").sort()
  );

  userAttributesResource: HttpResourceRef<PiResponse<Record<string, string>> | undefined> =
    new MockHttpResourceRef<PiResponse<Record<string, string>> | undefined>(
      MockPiResponse.fromValue<Record<string, string>>({
        department: "sales",
        city: "Berlin"
      })
    );

  userAttributes: Signal<Record<string, string>> = computed(
    () => this.userAttributesResource.value()?.result?.value ?? {}
  );

  userAttributesList: Signal<{ key: string; value: string }[]> = computed(() =>
    Object.entries(this.userAttributes()).map(([key, raw]) => ({
      key,
      value: Array.isArray(raw) ? raw.join(", ") : String(raw ?? "")
    }))
  );

  setUserAttribute = jest.fn().mockImplementation((key: string, value: string) => {
    const current = { ...this.userAttributes() };
    current[key] = value;

    (this.userAttributesResource as MockHttpResourceRef<
      PiResponse<Record<string, string>> | undefined
    >).set(MockPiResponse.fromValue<Record<string, string>>(current));

    return of(MockPiResponse.fromValue<number>(1));
  });

  deleteUserAttribute = jest.fn().mockImplementation((key: string) => {
    const current = { ...this.userAttributes() };
    delete current[key];

    (this.userAttributesResource as MockHttpResourceRef<
      PiResponse<Record<string, string>> | undefined
    >).set(MockPiResponse.fromValue<Record<string, string>>(current));

    return of(MockPiResponse.fromValue<boolean>(true));
  });

  detailsUsername: WritableSignal<string> = this.selectedUsername;
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

  userResource: HttpResourceRef<PiResponse<UserData[]> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue([]));

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

  usersResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue([]));

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

  selectionFilteredUsers = signal<UserData[]>([]);

  displayUser = jest.fn().mockImplementation((user: UserData | string): string => {
    const name = typeof user === "string" ? user : user?.username ?? "";
    this.selectedUsername.set(name);
    return name;
  });
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

  realmResource: HttpResourceRef<PiResponse<Realms> | undefined> =
    new MockHttpResourceRef<PiResponse<Realms> | undefined>(
      MockPiResponse.fromValue<Realms>({} as any)
    );

  realmOptions: Signal<string[]> = computed(() => {
    const realms = this.realmResource.value()?.result?.value as any;
    return realms ? Object.keys(realms) : [];
  });

  defaultRealmResource: HttpResourceRef<PiResponse<Realms> | undefined> =
    new MockHttpResourceRef<PiResponse<Realms> | undefined>(
      MockPiResponse.fromValue<Realms>(
        {
          realm1: {
            default: true,
            id: 1,
            option: "",
            resolver: []
          } as Realm
        } as any
      )
    );

  defaultRealm: Signal<string> = computed(() => {
    const data = this.defaultRealmResource.value()?.result?.value as any;
    return data ? Object.keys(data)[0] : "";
  });

  createRealm = jest
    .fn()
    .mockImplementation(
      (realm: string, nodeId: string, resolvers: { name: string; priority?: number | null }[]) => {
        const current = (this.realmResource.value()?.result?.value as any) ?? {};
        const existing: Realm | undefined = current[realm];

        const newResolverEntries = resolvers.map((r) => ({
          name: r.name,
          node: nodeId,
          type: "mock",
          priority: r.priority ?? null
        }));

        const updatedRealm: Realm = existing
          ? {
            ...existing,
            resolver: [
              ...(existing.resolver ?? []),
              ...newResolverEntries
            ]
          }
          : {
            default: false,
            id: Object.keys(current).length + 1,
            option: "",
            resolver: newResolverEntries
          };

        const updatedRealms = {
          ...current,
          [realm]: updatedRealm
        };

        (this.realmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
          MockPiResponse.fromValue<Realms>(updatedRealms as any)
        );

        return of(MockPiResponse.fromValue<any>({ realm, nodeId, resolvers }));
      }
    );

  deleteRealm = jest.fn().mockImplementation((realm: string) => {
    const current = (this.realmResource.value()?.result?.value as any) ?? {};
    if (current[realm]) {
      const { [realm]: _, ...rest } = current;
      (this.realmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
        MockPiResponse.fromValue<Realms>(rest as any)
      );
    }
    return of(MockPiResponse.fromValue<number>(1));
  });

  setDefaultRealm = jest.fn().mockImplementation((realm: string) => {
    const current = (this.realmResource.value()?.result?.value as any) ?? {};

    Object.keys(current).forEach((key) => {
      current[key] = {
        ...(current[key] as Realm),
        default: key === realm
      };
    });

    (this.realmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
      MockPiResponse.fromValue<Realms>(current as any)
    );

    (this.defaultRealmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
      MockPiResponse.fromValue<Realms>(
        {
          [realm]: current[realm] ??
            ({
              default: true,
              id: 1,
              option: "",
              resolver: []
            } as Realm)
        } as any
      )
    );

    return of(MockPiResponse.fromValue<number>(1));
  });
}

export class MockContentService implements ContentServiceInterface {
  detailsUsername: WritableSignal<string> = signal("");
  router: Router = {
    url: "/home",
    events: of({} as any)
  } as any;
  routeUrl: WritableSignal<string> = signal("/home");
  previousUrl: Signal<string> = signal("/home");
  tokenSerial: WritableSignal<string> = signal("");
  containerSerial: WritableSignal<string> = signal("");
  tokenSelected = jest.fn().mockImplementation((serial: string) => {
    this.tokenSerial.set(serial);
  });
  containerSelected = jest.fn().mockImplementation((serial: string) => {
    this.containerSerial.set(serial);
  });
  userSelected: (username: any) => void = jest.fn();
}

export class MockContainerService extends ContainerService {
  override containerBaseUrl: string = "mockEnvironment.proxyUrl + '/container'";
  override containerSerial = signal("CONT-1");
  override selectedContainer = signal("");
  override sort: WritableSignal<Sort> = signal({ active: "serial", direction: "asc" });
  override containerFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  override filterParams: Signal<Record<string, string>> = computed(() =>
    Object.fromEntries(
      Object.entries(this.containerFilter()).filter(([key]) =>
        [...this.apiFilter, ...this.advancedApiFilter].includes(key)
      )
    )
  );
  override pageSize: WritableSignal<number> = signal(10);
  override pageIndex: WritableSignal<number> = signal(0);
  override loadAllContainers: Signal<boolean> = signal(false);
  override containerResource: HttpResourceRef<PiResponse<ContainerDetails> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue({
      containers: [],
      count: 0
    })
  );
  override containerOptions: WritableSignal<string[]> = signal([]);
  override filteredContainerOptions: Signal<string[]> = computed(() => {
    const options = this.containerOptions();
    const filter = this.containerFilter();
    return options.filter((option) => option.includes(filter.value) || option.includes(filter.hiddenValue));
  });
  override containerSelection: WritableSignal<ContainerDetailData[]> = signal([]);
  override containerTypesResource: HttpResourceRef<PiResponse<ContainerTypes, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue<ContainerTypes>(new Map())
  );
  override containerTypeOptions: Signal<ContainerType[]> = computed(() => {
    return [{ "containerType": "generic", "description": "", "token_types": [] } as ContainerType,
      { "containerType": "smartphone", "description": "", "token_types": [] } as ContainerType,
      { "containerType": "yubikey", "description": "", "token_types": [] } as ContainerType];
  });
  override containerDetailResource = new MockHttpResourceRef(
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
          description: "",
          info: {}
        }
      ],
      count: 1
    })
  );
  override templatesResource: HttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined> =
    new MockHttpResourceRef(
      MockPiResponse.fromValue<{ templates: ContainerTemplate[] }>({
        templates: []
      })
    );
  override templates: WritableSignal<ContainerTemplate[]> = signal([]);
  override handleFilterInput = jest.fn().mockReturnValue(of({}));
  override addToken = jest.fn().mockReturnValue(of(null));
  override removeToken = jest.fn().mockReturnValue(of(null));
  override setContainerRealm = jest.fn().mockReturnValue(of(null));
  override setContainerDescription = jest.fn().mockReturnValue(of(null));
  override toggleActive = jest.fn().mockReturnValue(of({}));
  override unassignUser = jest.fn().mockReturnValue(of(null));
  override assignUser = jest.fn().mockReturnValue(of(null));
  override setContainerInfos = jest.fn().mockReturnValue(of({}));
  override deleteInfo = jest.fn().mockReturnValue(of({}));
  override addTokenToContainer = jest.fn().mockReturnValue(of(null));
  override removeTokenFromContainer = jest.fn().mockReturnValue(of({}));
  override toggleAll = jest.fn().mockReturnValue(of(null));
  override removeAll = jest.fn().mockReturnValue(of(null));
  override deleteContainer = jest.fn().mockReturnValue(of({}));
  override deleteAllTokens = jest.fn().mockReturnValue(of(null));

  override registerContainer(params: {
    container_serial: string;
    passphrase_prompt: string;
    passphrase_response: string;
  }): Observable<PiResponse<ContainerRegisterData, unknown>> {
    throw new Error("Method not implemented.");
  }

  override unregister = jest.fn().mockReturnValue(of({}));

  override containerBelongsToUser = jest.fn().mockReturnValue(true);

  override createContainer(param: {
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

export class MockTokenService extends TokenService {
  override tokenBaseUrl: string = "mockEnvironment.proxyUrl + '/token'";
  override tokenSerial = signal("MOCK_SERIAL");
  override filterParams: Signal<Record<string, string>> = signal({});
  override selectedTokenType: WritableSignal<TokenType> = signal({
    key: "hotp",
    name: "HOTP",
    info: "",
    text: "HMAC-based One-Time Password"
  });
  override showOnlyTokenNotInContainer = signal(false);
  override tokenFilter: WritableSignal<FilterValue> = signal(new FilterValue());

  override eventPageSize = 10;
  override userTokenResource: HttpResourceRef<PiResponse<Tokens> | undefined> =
    new MockHttpResourceRef<PiResponse<Tokens> | undefined>(
      MockPiResponse.fromValue<Tokens>({
        count: 0,
        current: 0,
        tokens: []
      })
    );

  override tokenDetailResource = new MockHttpResourceRef<PiResponse<Tokens>>(
    makeTokenDetailResponse("hotp")
  );
  override tokenTypesResource: HttpResourceRef<PiResponse<{}, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue({})
  );
  override tokenTypeOptions: WritableSignal<TokenType[]> = signal<TokenType[]>([
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
  override pageSize = signal(10);
  override tokenIsActive: WritableSignal<boolean> = signal(true);
  override tokenIsRevoked: WritableSignal<boolean> = signal(false);
  override pageIndex = signal(0);
  override tokenResource = new MockHttpResourceRef<PiResponse<Tokens> | undefined>(undefined as any);
  override tokenSelection: WritableSignal<TokenDetails[]> = signal<TokenDetails[]>([]);

  override bulkUnassignTokens(tokenDetails: TokenDetails[]): Observable<PiResponse<BulkResult, any>> {
    throw new Error("Method not implemented.");
  }

  override bulkDeleteTokens = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<BulkResult>({
    failed: [],
    unauthorized: [],
    count_success: 1
  })));
  override toggleActive = jest.fn().mockReturnValue(of({}));
  override resetFailCount = jest.fn().mockReturnValue(of(null));
  override saveTokenDetail = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<boolean>(true)));

  override getSerial(otp: string, params: HttpParams): Observable<PiResponse<{
    count: number;
    serial?: string
  }, unknown>> {
    throw new Error("Method not implemented.");
  }

  override setTokenInfos = jest.fn().mockReturnValue(of({}));
  override deleteToken = jest.fn().mockReturnValue(of({}));
  override revokeToken = jest.fn().mockReturnValue(of({}));
  override deleteInfo = jest.fn().mockReturnValue(of({}));
  override unassignUserFromAll = jest.fn().mockReturnValue(of([]));
  override unassignUser = jest.fn().mockReturnValue(of(null));
  override assignUserToAll = jest.fn().mockReturnValue(of([]));
  override assignUser = jest.fn().mockReturnValue(of(null));

  override setPin(tokenSerial: string, userPin: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  override setRandomPin(tokenSerial: string): Observable<Object> {
    throw new Error("Method not implemented.");
  }

  override resyncOTPToken = jest.fn().mockReturnValue(of(null));
  override getTokenDetails = jest.fn().mockReturnValue(of({}));
  override enrollToken = jest.fn().mockReturnValue(of({ detail: { serial: "X" } } as any));
  override lostToken = jest.fn<ReturnType<TokenService["lostToken"]>, Parameters<TokenService["lostToken"]>>()
    .mockImplementation((_serial: string) => {
      const response: LostTokenResponse = {
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
            disable: 1,
            end_date: "2025-01-31",
            init: true,
            password: "****",
            pin: false,
            serial: _serial,
            user: true,
            valid_to: "2025-02-28"
          }
        }
      };
      return of(response);
    });
  override stopPolling = jest.fn();
  override pollTokenRolloutState = jest
    .fn()
    .mockReturnValue(of({ result: { status: true, value: { tokens: [{ rollout_state: "enrolled" }] } } } as any));

  override setTokenRealm(tokenSerial: string, value: string[]): Observable<PiResponse<boolean, unknown>> {
    throw new Error("Method not implemented.");
  }

  override getTokengroups(): Observable<PiResponse<TokenGroups, unknown>> {
    throw new Error("Method not implemented.");
  }

  override setTokengroup(tokenSerial: string, value: string | string[]): Observable<Object> {
    throw new Error("Method not implemented.");
  }
}

export class MockMachineService implements MachineServiceInterface {
  baseUrl: string = "environment.mockProxyUrl + '/machine/'";
  filterValue: WritableSignal<Record<string, string>> = signal({});

  handleFilterInput($event: Event): void {
    throw new Error("Method not implemented.");
  }

  clearFilter(): void {
    throw new Error("Method not implemented.");
  }

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

  pickColumns<const K extends readonly ColumnKey[]>(
    ...keys: K
  ): {
    readonly [I in keyof K]: Readonly<{
      key: Extract<K[I], ColumnKey>;
      label: string;
    }>;
  } {
    return keys.map((k) => ({ key: k as Extract<typeof k, ColumnKey>, label: String(k) })) as any;
  }

  getColumnKeys<const C extends readonly ColumnDef[]>(
    cols: C
  ): {
    readonly [I in keyof C]: C[I] extends Readonly<{
        key: infer KK extends ColumnKey;
        label: string;
      }>
      ? KK
      : never;
  } {
    return cols.map((c) => c.key) as any;
  }

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

export class MockSystemService {
  nodes = jest.fn(() => [
    { uuid: "node-1", name: "Node 1" } as any,
    { uuid: "node-2", name: "Node 2" } as any
  ]);
}
