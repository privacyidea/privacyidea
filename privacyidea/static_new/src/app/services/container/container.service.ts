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
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { HttpClient, HttpErrorResponse, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { catchError, forkJoin, Observable, of, Subject, throwError } from "rxjs";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { ContainerTypeOption } from "../../components/token/container-create/container-create.component";
import { EnrollmentUrl } from "../../mappers/token-api-payload/_token-api-payload.mapper";
import { FilterValue } from "../../core/models/filter_value";
import { Sort } from "@angular/material/sort";
import { TokenService, TokenServiceInterface } from "../token/token.service";
import { StringUtils } from "../../utils/string.utils";
import { UserService, UserServiceInterface } from "../user/user.service";

const apiFilter = ["container_serial", "type", "user"];
const advancedApiFilter = ["token_serial"];

export interface ContainerDetails {
  count?: number;
  containers: Array<ContainerDetailData>;
}

export interface ContainerDetailData {
  description?: string;
  info?: any;
  internal_info_keys?: any[];
  last_authentication?: any;
  last_synchronization?: any;
  realms: string[];
  serial: string;
  states: string[];
  template?: string;
  tokens: ContainerDetailToken[];
  type: string;
  users: ContainerDetailUser[];
  select?: string;
  user_name?: string;
  user_realm?: string;
}

export interface ContainerDetailToken {
  active: boolean;
  container_serial: string;
  count: number;
  count_window: number;
  description: string;
  failcount: number;
  id: number;
  info?: {
    hashlib: string;
    tokenkind: string;
  };
  locked?: boolean;
  maxfail?: number;
  otplen?: number;
  realms?: string[];
  resolver?: string;
  revoked: boolean;
  rollout_state?: string;
  serial: string;
  sync_window: number;
  tokengroup: any[];
  tokentype: string;
  user_editable: false;
  user_id: string;
  user_realm: string;
  username: string;
}

export interface ContainerDetailUser {
  user_realm: string;
  user_name: string;
  user_resolver: string;
  user_id: string;
}

export type ContainerTypes = Map<ContainerTypeOption, _ContainerType>;

interface _ContainerType {
  description: string;
  token_types: string[];
}

export interface ContainerType {
  containerType: ContainerTypeOption;
  description: string;
  token_types: string[];
}

export interface ContainerTemplate {
  container_type: string;
  default: boolean;
  name: string;
  template_options: {
    options: any;
    tokens: Array<ContainerTemplateToken>;
  };
}

export interface ContainerTemplateToken {
  genkey: boolean;
  hashlib: string;
  otplen: number;
  timeStep: number;
  type: string;
  user: boolean;
}

export interface ContainerRegisterData {
  container_url: EnrollmentUrl;
  hash_algorithm: string;
  key_algorithm: string;
  nonce: string;
  offline_tokens: any[];
  passphrase_prompt: string;
  server_url: string;
  ssl_verify: boolean;
  time_stamp: string;
  ttl: number;
}

export interface ContainerUnregisterData {
  success: boolean;
}

export interface ContainerServiceInterface {
  compatibleWithTokenType: WritableSignal<string | null>;
  isPollingActive: Signal<boolean>;
  apiFilter: string[];
  advancedApiFilter: string[];
  stopPolling$: Subject<void>;
  containerBaseUrl: string;
  eventPageSize: number;
  states: WritableSignal<string[]>;
  containerSerial: WritableSignal<string>;
  selectedContainer: WritableSignal<string | null>;
  sort: WritableSignal<Sort>;
  containerFilter: WritableSignal<FilterValue>;
  filterParams: Signal<Record<string, string>>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  loadAllContainers: Signal<boolean>;
  containerResource: HttpResourceRef<PiResponse<ContainerDetails> | undefined>;
  containerOptions: Signal<string[]>;
  filteredContainerOptions: Signal<string[]>;
  containerSelection: WritableSignal<ContainerDetailData[]>;
  containerTypesResource: HttpResourceRef<PiResponse<ContainerTypes> | undefined>;
  containerTypeOptions: Signal<ContainerType[]>;
  selectedContainerType: Signal<ContainerType>;
  containerDetailResource: HttpResourceRef<PiResponse<ContainerDetails> | undefined>;
  containerDetail: WritableSignal<ContainerDetails>;
  templatesResource: HttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }> | undefined>;
  templates: Signal<ContainerTemplate[]>;
  addToken: (tokenSerial: string, containerSerial: string) => Observable<any>;
  removeToken: (tokenSerial: string, containerSerial: string) => Observable<any>;
  setContainerRealm: (containerSerial: string, value: string[]) => Observable<any>;
  setContainerDescription: (containerSerial: string, value: string) => Observable<any>;
  toggleActive: (
    containerSerial: string,
    states: string[]
  ) => Observable<PiResponse<{ disabled: boolean } | { active: boolean }>>;
  unassignUser: (containerSerial: string, username: string, userRealm: string) => Observable<any>;
  assignUser: (args: {
    containerSerial: string;
    username: string;

    userRealm: string;
  }) => Observable<any>;
  setContainerInfos: (containerSerial: string, infos: any) => Observable<Object>[];
  deleteInfo: (containerSerial: string, key: string) => Observable<any>;
  addTokenToContainer: (containerSerial: string, tokenSerial: string) => Observable<any>;
  removeTokenFromContainer: (containerSerial: string, tokenSerial: string) => Observable<any>;
  toggleAll: (action: "activate" | "deactivate") => Observable<any>;
  removeAll: (containerSerial: string) => Observable<any>;
  deleteContainer: (containerSerial: string) => Observable<any>;
  deleteAllTokens: (param: { containerSerial: string; serialList: string }) => Observable<any>;
  registerContainer: (params: {
    container_serial: string;
    passphrase_user: boolean;
    passphrase_prompt: string;
    passphrase_response: string;
    rollover?: boolean;
  }) => Observable<PiResponse<ContainerRegisterData>>;
  unregister: (containerSerial: string) => Observable<PiResponse<any>>;
  containerBelongsToUser: (containerSerial: string) => false | true | undefined;

  handleFilterInput($event: Event): void;

  clearFilter(): void;

  stopPolling(): void;

  createContainer(param: {
    container_type: string;
    description?: string;
    template_name?: string;
    user?: string;
    realm?: string;
  }): Observable<PiResponse<{ container_serial: string }>>;

  startPolling(containerSerial: string): void;
}

@Injectable({
  providedIn: "root"
})
export class ContainerService implements ContainerServiceInterface {
  private readonly http: HttpClient = inject(HttpClient);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly userService: UserServiceInterface = inject(UserService);
  private readonly pollingTrigger = signal<number>(0);
  private readonly isRolloverPolling = signal(false);
  readonly compatibleWithTokenType: WritableSignal<string | null> = signal<string | null>(null);
  readonly isPollingActive = signal(false);
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;

  stopPolling$ = new Subject<void>();
  containerBaseUrl = environment.proxyUrl + "/container/";
  eventPageSize = 10;

  states = signal<string[]>([]);
  containerSerial = this.contentService.containerSerial;
  selectedContainer: WritableSignal<string | null> = linkedSignal({
    source: () => ({
      routeUrl: this.contentService.routeUrl()
    }),
    computation: (source, previous) =>
      source.routeUrl === ROUTE_PATHS.TOKENS_ENROLLMENT ? (previous?.value ?? "") : ""
  });
  sort = signal<Sort>({ active: "serial", direction: "asc" });
  containerFilter: WritableSignal<FilterValue> = linkedSignal({
    source: this.contentService.routeUrl,
    computation: () => new FilterValue()
  });
  filterParams = computed<Record<string, string>>(() => {
    const allowed = [...this.apiFilter, ...this.advancedApiFilter];

    const plainKeys = new Set(["user", "type", "container_serial", "token_serial"]);

    const entries = Array.from(this.containerFilter().filterMap.entries())
      .filter(([key]) => allowed.includes(key))
      .map(([key, value]) => [key, (value ?? "").toString().trim()] as const)
      .filter(([, v]) => StringUtils.validFilterValue(v))
      .map(([key, v]) => [key, plainKeys.has(key) ? v : `*${v}*`] as const);

    return Object.fromEntries(entries) as Record<string, string>;
  });

  pageSize = linkedSignal({
    source: this.containerFilter,
    computation: (): any => {
      if (![5, 10, 15].includes(this.eventPageSize)) {
        return 10;
      }
      return this.eventPageSize;
    }
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.containerFilter(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: () => 0
  });
  loadAllContainers = computed(() => {
    return (
      [ROUTE_PATHS.TOKENS_ENROLLMENT].includes(this.contentService.routeUrl()) ||
      this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS)
    );
  });

  private readonly uniqueCompatibleType = computed<string | null>(() => {
    const tt = this.compatibleWithTokenType();
    if (!tt) return null;

    const types = this.containerTypeOptions();
    const compatible = types.filter(t => (t.token_types ?? []).includes(tt));

    return compatible.length === 1 ? String(compatible[0].containerType) : null;
  });

  containerResource = httpResource<PiResponse<ContainerDetails>>(() => {
    if (
      (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS) &&
        !this.contentService.routeUrl().startsWith(ROUTE_PATHS.USERS_DETAILS) &&
        ![ROUTE_PATHS.TOKENS_CONTAINERS, ROUTE_PATHS.TOKENS_ENROLLMENT, ROUTE_PATHS.TOKENS].includes(
          this.contentService.routeUrl()
        )) ||
      (this.authService.role() === "admin" && this.contentService.routeUrl() === ROUTE_PATHS.TOKENS) ||
      !this.authService.actionAllowed("container_list")
    ) {
      return undefined;
    }

    const baseParams: Record<string, any> = {
      ...(!this.loadAllContainers() && {
        page: this.pageIndex() + 1,
        pagesize: this.pageSize()
      }),
      ...(this.loadAllContainers() && { no_token: 1 }),
      sortby: this.sort().active,
      sortdir: this.sort().direction,
      ...this.filterParams(),
      user: this.userService.selectedUser()?.username ?? ""
    };

    const autoType = this.uniqueCompatibleType();
    if (autoType && !('type' in baseParams) && !('type_list' in baseParams)) {
      baseParams["type"] = autoType;
    }

    return {
      url: this.containerBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: baseParams
    };
  });
  containerOptions = linkedSignal({
    source: this.containerResource.value,
    computation: (containerResource) => {
      return containerResource?.result?.value?.containers.map((container) => container.serial) ?? [];
    }
  });
  filteredContainerOptions = computed(() => {
    const filter = (this.selectedContainer() || "").toLowerCase();
    return this.containerOptions().filter((option) => option.toLowerCase().includes(filter));
  });

  containerSelection: WritableSignal<ContainerDetailData[]> = linkedSignal({
    source: () => ({
      pageIndex: this.pageIndex(),
      pageSize: this.pageSize(),
      sort: this.sort(),
      filterValue: this.containerFilter()
    }),
    computation: () => []
  });

  containerTypesResource = httpResource<PiResponse<ContainerTypes>>(() => {
    const route = this.contentService.routeUrl();
    if (![ROUTE_PATHS.TOKENS_CONTAINERS_CREATE, ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD,
      ROUTE_PATHS.TOKENS_ENROLLMENT]
        .includes(route) && !route.startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
      return undefined;
    }
    return {
      url: `${this.containerBaseUrl}types`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  containerTypeOptions = computed<ContainerType[]>(() => {
    const value = this.containerTypesResource.value()?.result?.value;
    if (!value) {
      return [];
    }
    return Array.from(Object.entries(value)).map(([key, containerType]) => ({
      containerType: key as ContainerTypeOption,
      description: containerType?.description ?? "",
      token_types: containerType?.token_types ?? []
    }));
  });

  selectedContainerType = linkedSignal({
    source: this.contentService.routeUrl,
    computation: () => {
      let containerType = this.authService.defaultContainerType();
      if (this.contentService.routeUrl() === ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD) {
        containerType = this.authService.containerWizard().type || containerType;
      }
      return (
        this.containerTypeOptions().find((type) => type.containerType === containerType) ||
        this.containerTypeOptions()[0] || {
          containerType: "generic",
          description: "No container type data available",
          token_types: []
        }
      );
    }
  });

  containerDetailResource = httpResource<PiResponse<ContainerDetails>>(() => {
    const serial = this.containerSerial();
    const trigger = this.pollingTrigger();
    const active = this.isPollingActive();

    if (serial === "") {
      return undefined;
    }
    return {
      url: this.containerBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        container_serial: serial
      }
    };
  });
  containerDetail: WritableSignal<ContainerDetails> = linkedSignal({
    source: this.containerDetailResource.value,
    computation: (containerDetailResource, previous) => {
      if (containerDetailResource?.result?.value) {
        return containerDetailResource.result?.value;
      }
      return (
        previous?.value ?? {
          containers: [],
          count: 0
        }
      );
    }
  });

  templatesResource = httpResource<PiResponse<{ templates: ContainerTemplate[] }>>(() => {
    if (
      this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CONTAINERS_CREATE ||
      !this.authService.actionAllowed("container_template_list")
    ) {
      return undefined;
    }
    return {
      url: `${this.containerBaseUrl}templates`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  templates: WritableSignal<ContainerTemplate[]> = linkedSignal({
    source: this.templatesResource.value,
    computation: (templatesResource, previous) => templatesResource?.result?.value?.templates ?? previous?.value ?? []
  });

  constructor() {
    effect(() => {
      if (this.containerDetailResource.error()) {
        const containerDetailError = this.containerDetailResource.error() as HttpErrorResponse;
        console.error("Failed to get container details.", containerDetailError.message);
        const message = containerDetailError.error?.result?.error?.message || containerDetailError.message;
        this.notificationService.openSnackBar("Failed to get container details." + message);
      }
    });
    effect(() => {
      if (this.containerResource.error()) {
        const error = this.containerResource.error() as HttpErrorResponse;
        this.notificationService.openSnackBar(error.message);
      }
    });

    effect(() => {
      clearTimeout(this.pollingTimeoutId);
      this.pollingTrigger();
      const serial = this.containerSerial();
      const resourceValue = this.containerDetailResource.value();
      const active = this.isPollingActive();

      const routeUrl = this.contentService.routeUrl();
      const onAllowedRoute =
        routeUrl === ROUTE_PATHS.TOKENS_CONTAINERS_CREATE ||
        routeUrl.startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS);

      if (!active || !serial || !resourceValue?.result?.value || !onAllowedRoute) {
        return;
      }

      const containerData = resourceValue.result.value.containers[0];
      const registrationState = containerData?.info?.registration_state;

      if (registrationState !== "registered") {
        this.pollingTimeoutId = setTimeout(() => {
          this.pollingTrigger.update(count => count + 1);
        }, 2000);
      } else {
        const isRollover = this.isRolloverPolling();
        if (isRollover) {
          this.notificationService.openSnackBar("Container rollover completed successfully.");
        } else if (routeUrl !== ROUTE_PATHS.TOKENS_CONTAINERS_CREATE) {
          // container create shows a dialog on successful registration
          this.notificationService.openSnackBar("Container registered successfully.");
        }
        this.isPollingActive.set(false);
        this.isRolloverPolling.set(false);
      }
    });
  }

  addToken(tokenSerial: string, containerSerial: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<boolean>>(`${this.containerBaseUrl}${containerSerial}/add`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to assign container.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to assign container. " + message);
          return throwError(() => error);
        })
      );
  }

  removeToken(tokenSerial: string, containerSerial: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<
        PiResponse<boolean>
      >(`${this.containerBaseUrl}${containerSerial}/remove`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to unassign container.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to unassign container. " + message);
          return throwError(() => error);
        })
      );
  }

  setContainerRealm(containerSerial: string, value: string[]): Observable<any> {
    const headers = this.authService.getHeaders();
    const valueString = value ? value.join(",") : "";
    return this.http
      .post(`${this.containerBaseUrl}${containerSerial}/realms`, { realms: valueString }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to set container realm.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set container realm. " + message);
          return throwError(() => error);
        })
      );
  }

  setContainerDescription(containerSerial: string, value: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(`${this.containerBaseUrl}${containerSerial}/description`, { description: value }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to set container description.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set container description. " + message);
          return throwError(() => error);
        })
      );
  }

  toggleActive(
    containerSerial: string,
    states: string[]
  ): Observable<PiResponse<{ disabled: boolean } | { active: boolean }>> {
    const headers = this.authService.getHeaders();
    let new_states = states
      .map((state) => {
        if (state === "active") {
          return "disabled";
        } else if (state === "disabled") {
          return "active";
        } else {
          return state;
        }
      })
      .join(",");
    if (!(states.includes("active") || states.includes("disabled"))) {
      new_states = states.concat("active").join(",");
    }
    return this.http
      .post<
        PiResponse<{ disabled: boolean } | { active: boolean }>
      >(`${this.containerBaseUrl}${containerSerial}/states`, { states: new_states }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to toggle active.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to toggle active. " + message);
          return throwError(() => error);
        })
      );
  }

  unassignUser(containerSerial: string, username: string, userRealm: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(`${this.containerBaseUrl}${containerSerial}/unassign`, { user: username, realm: userRealm }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to unassign user.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to unassign user. " + message);
          return throwError(() => error);
        })
      );
  }

  assignUser(args: { containerSerial: string; username: string; userRealm: string }): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(
        `${this.containerBaseUrl}${args.containerSerial}/assign`,
        { user: args.username, realm: args.userRealm },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to assign user.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to assign user. " + message);
          return throwError(() => error);
        })
      );
  }

  setContainerInfos(containerSerial: string, infos: any): Observable<Object>[] {
    const headers = this.authService.getHeaders();
    const info_url = `${this.containerBaseUrl}${containerSerial}/info`;
    return Object.keys(infos).map((info) => {
      const infoValue = infos[info];
      return this.http.post(`${info_url}/${info}`, { value: infoValue }, { headers }).pipe(
        catchError((error) => {
          console.error("Failed to save container infos.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to save container infos. " + message);
          return throwError(() => error);
        })
      );
    });
  }

  deleteInfo(containerSerial: string, key: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete(`${this.containerBaseUrl}${containerSerial}/info/delete/${key}`, {
        headers
      })
      .pipe(
        catchError((error) => {
          console.error("Failed to delete info.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to delete info. " + message);
          return throwError(() => error);
        })
      );
  }

  addTokenToContainer(containerSerial: string, tokenSerial: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.post(`${this.containerBaseUrl}${containerSerial}/add`, { serial: tokenSerial }, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to add token to container.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to add token to container. " + message);
        return throwError(() => error);
      })
    );
  }

  removeTokenFromContainer(containerSerial: string, tokenSerial: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(`${this.containerBaseUrl}${containerSerial}/remove`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to remove token from container.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to remove token from container. " + message);
          return throwError(() => error);
        })
      );
  }

  toggleAll(action: "activate" | "deactivate"): Observable<(PiResponse<boolean> | null)[] | null> {
    const data = this.containerDetail();

    if (!data || !Array.isArray(data.containers[0].tokens)) {
      this.notificationService.openSnackBar("No valid tokens array found in data.");
      return of(null);
    }

    const tokensForAction =
      action === "activate"
        ? data.containers[0].tokens.filter((token) => !token.active)
        : data.containers[0].tokens.filter((token) => token.active);

    if (tokensForAction.length === 0) {
      this.notificationService.openSnackBar("No tokens for action.");
      return of(null);
    }
    return forkJoin(
      tokensForAction.map((token: { serial: string; active: boolean; revoked: boolean }) => {
        return !token.revoked ? this.tokenService.toggleActive(token.serial, token.active) : of(null);
      })
    ).pipe(
      catchError((error) => {
        console.error("Failed to toggle all.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to toggle all. " + message);
        return throwError(() => error);
      })
    );
  }

  removeAll(containerSerial: string): Observable<PiResponse<boolean> | null> {
    const data = this.containerDetail();

    if (!data || !Array.isArray(data.containers[0].tokens)) {
      console.error("No valid tokens array found in data.", data);
      this.notificationService.openSnackBar("No valid tokens array found in data.");
      return of(null);
    }

    const tokensForAction = data.containers[0].tokens.map((token) => token.serial);

    if (tokensForAction.length === 0) {
      console.error("No tokens to remove. Returning []");
      this.notificationService.openSnackBar("No tokens to remove.");
      return of(null);
    }

    const headers = this.authService.getHeaders();

    return this.http
      .post<
        PiResponse<boolean>
      >(`${this.containerBaseUrl}${containerSerial}/removeall`, { serial: tokensForAction.join(",") }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to remove all.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to remove all. " + message);
          return throwError(() => error);
        })
      );
  }

  deleteContainer(containerSerial: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.delete(`${this.containerBaseUrl}${containerSerial}`, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to delete container.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete container. " + message);
        return throwError(() => error);
      })
    );
  }

  deleteAllTokens(param: { containerSerial: string; serialList: string }): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(`${this.containerBaseUrl}${param.containerSerial}/removeall`, { serial: param.serialList }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to delete all tokens.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to delete all tokens. " + message);
          return throwError(() => error);
        })
      );
  }

  registerContainer(params: {
    container_serial: string;
    passphrase_user: boolean;
    passphrase_prompt: string;
    passphrase_response: string;
    rollover?: boolean;
  }): Observable<PiResponse<ContainerRegisterData>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<ContainerRegisterData>>(
        `${this.containerBaseUrl}register/initialize`,
        params,
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to register container.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to register container. " + message);
          return throwError(() => error);
        })
      );
  }

  unregister(containerSerial: string) {
    this.stopPolling();
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<ContainerUnregisterData>>(
        `${this.containerBaseUrl}register/${containerSerial}/terminate`,
        {},
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to unregister container.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to unregister container. " + message);
          return throwError(() => error);
        })
      );
  }

  containerBelongsToUser(containerSerial: any): false | true | undefined {
    return this.containerResource
      .value()
      ?.result?.value?.containers?.some((container) => container.serial === containerSerial);
  }

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    const newFilter = this.containerFilter().copyWith({ value: input.value });
    this.containerFilter.set(newFilter);
  }

  clearFilter(): void {
    this.containerFilter.set(new FilterValue());
  }

  stopPolling(): void {
    clearTimeout(this.pollingTimeoutId);
    this.isPollingActive.set(false);
    this.stopPolling$.next();
  }

  createContainer(param: {
    container_type: string;
    description?: string;
    template_name?: string;
    user?: string;
    realm?: string;
  }): Observable<PiResponse<{ container_serial: string }>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<{ container_serial: string }>>(
        `${this.containerBaseUrl}init`,
        {
          type: param.container_type,
          description: param.description,
          user: param.user,
          realm: param.realm,
          template_name: param.template_name
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to create container.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to create container. " + message);
          return throwError(() => error);
        })
      );
  }

  startPolling(containerSerial: string, isRollover: boolean = false): void {
    if (this.isPollingActive()) {
      return;
    }
    this.containerSerial.set(containerSerial);
    this.isRolloverPolling.set(isRollover);
    this.isPollingActive.set(true);
    this.pollingTrigger.update(count => count + 1);
  }

  private pollingTimeoutId: any;
}
