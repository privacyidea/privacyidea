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
import { HttpClient, HttpErrorResponse, HttpParams, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { forkJoin, Observable, Subject, switchMap, throwError, timer } from "rxjs";
import { catchError, shareReplay, takeUntil, takeWhile } from "rxjs/operators";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { TokenTypeOption as TokenTypeKey } from "../../components/token/token.component";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../mappers/token-api-payload/_token-api-payload.mapper";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { tokenTypes } from "../../utils/token.utils";
import { FilterValue } from "../../core/models/filter_value";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";

const apiFilter = [
  "serial",
  "type",
  "active",
  "description",
  "rollout_state",
  "user",
  "tokenrealm",
  "container_serial"
];
const advancedApiFilter = ["infokey & infovalue", "userid", "resolver", "assigned"];
const hiddenApiFilter = ["type_list"];

export interface Tokens {
  count: number;
  current: number;
  next?: number;
  page?: number;
  tokens: TokenDetails[];
}

export interface TokenDetails {
  active: boolean;
  container_serial: string;
  count: number;
  count_window: number;
  description: string;
  failcount: number;
  id: number;
  info: any;
  locked: boolean;
  maxfail: number;
  otplen: number;
  realms: string[];
  resolver: string;
  revoked: boolean;
  rollout_state: string;
  serial: string;
  sync_window: number;
  tokengroup: TokenGroup[];
  tokentype: TokenTypeKey;
  user_id: string;
  user_realm: string;
  username: string;
}

export type TokenGroups = Map<string, TokenGroup[]>;

export interface TokenGroup {
  id: number;
  description: string;
}

export interface TokenType {
  key: TokenTypeKey;
  info: string;
  text: string;
}

export interface WebAuthnRegisterRequest {
  attestation: string;
  authenticatorSelection: {
    userVerification: string;
  };
  displayName: string;
  message: string;
  name: string;
  nonce: string;
  excludeCredentials?: any;
  extensions?: any;
  pubKeyCredAlgorithms: {
    alg: number;
    type: string;
  }[];
  relyingParty: {
    id: string;
    name: string;
  };
  serialNumber: string;
  timeout: number;
  transaction_id: string;
}

export type LostTokenResponse = PiResponse<LostTokenData>;

export interface LostTokenData {
  disable: number;
  end_date: string;
  init: boolean;
  password: string;
  pin: boolean;
  serial: string;
  user: boolean;
  valid_to: string;
}

export interface BulkResult {
  failed: string[];
  unauthorized: string[];
  count_success: number;
}

export interface TokenServiceInterface {
  stopPolling$: Subject<void>;
  tokenBaseUrl: string;
  eventPageSize: number;
  tokenSerial: WritableSignal<string>;
  selectedTokenType: Signal<TokenType>;
  showOnlyTokenNotInContainer: WritableSignal<boolean>;
  tokenFilter: WritableSignal<FilterValue>;

  clearFilter(): void;

  handleFilterInput($event: Event): void;

  tokenDetailResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  tokenTypesResource: HttpResourceRef<PiResponse<{}> | undefined>;
  tokenTypeOptions: Signal<TokenType[]>;
  pageSize: WritableSignal<number>;
  tokenIsActive: WritableSignal<boolean>;
  tokenIsRevoked: WritableSignal<boolean>;
  defaultSizeOptions: number[];
  apiFilter: string[];
  advancedApiFilter: string[];

  sort: WritableSignal<Sort>;
  pageIndex: WritableSignal<number>;
  tokenResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  tokenSelection: WritableSignal<TokenDetails[]>;

  toggleActive(tokenSerial: string, active: boolean): Observable<PiResponse<boolean>>;

  resetFailCount(tokenSerial: string): Observable<PiResponse<boolean>>;

  saveTokenDetail(tokenSerial: string, key: string, value: any): Observable<PiResponse<boolean>>;

  getSerial(
    otp: string,
    params: HttpParams
  ): Observable<PiResponse<{ count: number; serial?: string | undefined }>>;

  setTokenInfos(tokenSerial: string, infos: any): Observable<PiResponse<boolean>[]>;

  deleteToken(tokenSerial: string): Observable<Object>;

  bulkDeleteTokens(selectedTokens: TokenDetails[]): Observable<PiResponse<BulkResult, any>>;

  revokeToken(tokenSerial: string): Observable<any>;

  deleteInfo(tokenSerial: string, infoKey: string): Observable<Object>;

  unassignUserFromAll(tokenSerials: string[]): Observable<PiResponse<boolean>[]>;

  unassignUser(tokenSerial: string): Observable<PiResponse<boolean>>;

  bulkUnassignTokens(tokenDetails: TokenDetails[]): Observable<PiResponse<BulkResult, any>>;

  assignUserToAll(args: {
    tokenSerials: string[];
    username: string;
    realm: string;
    pin?: string;
  }): Observable<PiResponse<boolean>[]>;

  assignUser(args: {
    tokenSerial: string;
    username: string;
    realm: string;
    pin?: string;
  }): Observable<PiResponse<boolean>>;

  setPin(tokenSerial: string, userPin: string): Observable<any>;

  setRandomPin(tokenSerial: string): Observable<any>;

  resyncOTPToken(tokenSerial: string, firstOTPValue: string, secondOTPValue: string): Observable<Object>;

  getTokenDetails(tokenSerial: string): Observable<PiResponse<Tokens>>;

  enrollToken<T extends TokenEnrollmentData, R extends EnrollmentResponse>(args: {
    data: T;
    mapper: TokenApiPayloadMapper<T>;
  }): Observable<R>;

  lostToken(tokenSerial: string): Observable<LostTokenResponse>;

  stopPolling(): void;

  pollTokenRolloutState(args: { tokenSerial: string; initDelay: number }): Observable<PiResponse<Tokens>>;

  setTokenRealm(tokenSerial: string, value: string[]): Observable<PiResponse<boolean>>;

  getTokengroups(): Observable<PiResponse<TokenGroups>>;

  setTokengroup(tokenSerial: string, value: string | string[]): Observable<Object>;
}

@Injectable({
  providedIn: "root"
})
export class TokenService implements TokenServiceInterface {
  private readonly http: HttpClient = inject(HttpClient);

  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly hiddenApiFilter = hiddenApiFilter;
  stopPolling$ = new Subject<void>();
  tokenBaseUrl = environment.proxyUrl + "/token/";
  eventPageSize = 10;
  tokenSerial = this.contentService.tokenSerial;

  constructor() {
    effect(() => {
      if (this.tokenResource.error()) {
        let tokensResourceError = this.tokenResource.error() as HttpErrorResponse;
        console.error("Failed to get token data.", tokensResourceError.message);
        this.notificationService.openSnackBar(tokensResourceError.message);
      }
    });
    effect(() => {
      if (this.tokenTypesResource.error()) {
        let tokenTypesResourceError = this.tokenTypesResource.error() as HttpErrorResponse;
        console.error("Failed to get token type data.", tokenTypesResourceError.message);
        this.notificationService.openSnackBar(tokenTypesResourceError.message);
      }
    });
  }

  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  readonly defaultSizeOptions = [5, 10, 25, 50];
  tokenIsActive = signal(true);
  tokenIsRevoked = signal(true);

  showOnlyTokenNotInContainer = linkedSignal({
    source: this.contentService.routeUrl,
    computation: (routeUrl) => {
      return routeUrl.startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS);
    }
  });
  tokenFilter: WritableSignal<FilterValue> = linkedSignal({
    source: () => ({
      showOnlyTokenNotInContainer: this.showOnlyTokenNotInContainer(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: (source, previous) => {
      if (!source.routeUrl.startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS)) {
        return new FilterValue();
      }
      if (!previous || source.routeUrl !== previous.source.routeUrl) {
        return new FilterValue({ hiddenValue: source.showOnlyTokenNotInContainer ? "container_serial:" : " " });
      }
      const filterValue = previous.value;
      if (source.showOnlyTokenNotInContainer) {
        return filterValue.addHiddenKey("container_serial");
      } else {
        return filterValue.removeHiddenKey("container_serial");
      }
    }
  });

  clearFilter(): void {
    this.tokenFilter.set(new FilterValue());
  }

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    const newFilter = this.tokenFilter().copyWith({ value: input.value.trim() });
    this.tokenFilter.set(newFilter);
  }

  tokenDetailResource = httpResource<PiResponse<Tokens>>(() => {
    if (!this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_DETAILS, 0)) {
      return undefined;
    }
    return {
      url: this.tokenBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: { serial: this.tokenSerial() }
    };
  });

  tokenTypesResource = httpResource<PiResponse<{}>>(() => {
    if (![ROUTE_PATHS.TOKENS_ENROLLMENT, ROUTE_PATHS.TOKENS_GET_SERIAL].includes(this.contentService.routeUrl())) {
      return undefined;
    }
    return {
      url: environment.proxyUrl + "/auth/rights",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  tokenTypeOptions = computed<TokenType[]>(() => {
    const obj = this.tokenTypesResource?.value()?.result?.value;
    if (!obj) return [];
    return Object.entries(obj).map(([key, info]) => ({
      key: key as TokenTypeKey,
      info: String(info),
      text: tokenTypes.find((t) => t.key === key)?.text || ""
    }));
  });

  selectedTokenType = linkedSignal({
    source: () => ({
      tokenTypeOptions: this.tokenTypeOptions(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: (source) =>
      source.tokenTypeOptions.find((type) => type.key === this.authService.defaultTokentype()) ||
      source.tokenTypeOptions[0] ||
      ({ key: "hotp", info: "", text: "" } as TokenType)
  });

  pageSize = linkedSignal<{ role: string }, number>({
    source: () => ({
      role: this.authService.role()
    }),
    computation: (source, previous) => {
      if (previous && source.role === previous.source.role) {
        return previous.value;
      }
      if (this.authService.tokenPageSize() != null && this.authService.tokenPageSize()! > 0) {
        return this.authService.tokenPageSize()!;
      }
      return source.role === "user" ? 5 : 10;
    }
  });
  sort = signal({ active: "serial", direction: "asc" } as Sort);

  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.tokenFilter(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl(),
      sort: this.sort()
    }),
    computation: () => 0
  });

  filterParams = computed<Record<string, string>>(() => {
    const allowedFilters = [...this.apiFilter, ...this.advancedApiFilter, ...this.hiddenApiFilter];

    let filterPairs = [
      ...Array.from(this.tokenFilter().filterMap.entries()),
      ...Array.from(this.tokenFilter().hiddenFilterMap.entries())
    ];
    let filterPairsMap = filterPairs
      .filter(([key]) => allowedFilters.includes(key))
      .map(([key, value]) => ({ key, value }));
    return filterPairsMap.reduce(
      (acc, { key, value }) => ({
        ...acc,
        [key]: ["user", "infokey", "infovalue", "active", "assigned", "container_serial"].includes(key)
          ? `${value}`
          : `*${value}*`
      }),
      {} as Record<string, string>
    );
  });

  tokenResource = httpResource<PiResponse<Tokens>>(() => {
    if (
      this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS &&
      !this.contentService.routeUrl().includes(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS)
    ) {
      return undefined;
    }
    return {
      url: this.tokenBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        page: this.pageIndex() + 1,
        pagesize: this.pageSize(),
        sortby: this.sort()?.active || "serial",
        sortdir: this.sort()?.direction || "asc",
        ...this.filterParams()
      }
    };
  });

  tokenSelection: WritableSignal<TokenDetails[]> = linkedSignal({
    source: () => ({
      routeUrl: this.contentService.routeUrl(),
      tokenResource: this.tokenResource.value()
    }),
    computation: () => []
  });

  bulkUnassignTokens(tokenDetails: TokenDetails[]): Observable<PiResponse<BulkResult, any>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<BulkResult, any>>(
        this.tokenBaseUrl + "unassign",
        {
          serials: tokenDetails.map((token) => token.serial)
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to unassign tokens.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to unassign tokens. " + message);
          return throwError(() => error);
        })
      );
  }

  bulkDeleteTokens(selectedTokens: TokenDetails[]): Observable<PiResponse<BulkResult, any>> {
    const headers = this.authService.getHeaders();
    const body = { serials: selectedTokens.map((t) => t.serial) };

    return this.http.delete<PiResponse<BulkResult, any>>(this.tokenBaseUrl, { headers, body }).pipe(
      catchError((error) => {
        console.error("Failed to delete tokens.", error);
        const message = error.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete tokens. " + message);
        return throwError(() => error);
      })
    );
  }

  toggleActive(tokenSerial: string, active: boolean): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    const action = active ? "disable" : "enable";
    return this.http
      .post<PiResponse<boolean>>(`${this.tokenBaseUrl}${action}`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to toggle active.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to toggle active. " + message);
          return throwError(() => error);
        })
      );
  }

  resetFailCount(tokenSerial: string): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    return this.http.post<PiResponse<boolean>>(this.tokenBaseUrl + "reset", { serial: tokenSerial }, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to reset fail count.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to reset fail count. " + message);
        return throwError(() => error);
      })
    );
  }

  saveTokenDetail(tokenSerial: string, key: string, value: any): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;

    const params =
      key === "maxfail" ? { serial: tokenSerial, max_failcount: value } : { serial: tokenSerial, [key]: value };

    return this.http.post<PiResponse<boolean>>(set_url, params, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to set token detail.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to set token detail. " + message);
        return throwError(() => error);
      })
    );
  }

  setTokenInfos(tokenSerial: string, infos: any): Observable<PiResponse<boolean>[]> {
    const headers = this.authService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;
    const info_url = `${this.tokenBaseUrl}info`;

    const postRequest = (url: string, body: any) => {
      return this.http.post<PiResponse<boolean>>(url, body, { headers }).pipe(
        catchError((error) => {
          console.error("Failed to set token info.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set token info. " + message);
          return throwError(() => error);
        })
      );
    };

    const requests = Object.keys(infos).map((infoKey) => {
      const infoValue = infos[infoKey];
      if (
        infoKey === "count_auth_max" ||
        infoKey === "count_auth_success_max" ||
        infoKey === "hashlib" ||
        infoKey === "validity_period_start" ||
        infoKey === "validity_period_end"
      ) {
        return postRequest(set_url, {
          serial: tokenSerial,
          [infoKey]: infoValue
        });
      } else {
        return postRequest(`${info_url}/${tokenSerial}/${infoKey}`, {
          value: infoValue
        });
      }
    });
    return forkJoin(requests);
  }

  deleteToken(tokenSerial: string): Observable<Object> {
    const headers = this.authService.getHeaders();
    return this.http.delete(this.tokenBaseUrl + tokenSerial, { headers });
  }

  revokeToken(tokenSerial: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}revoke`, { serial: tokenSerial }, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to revoke token.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to revoke token. " + message);
        return throwError(() => error);
      })
    );
  }

  deleteInfo(tokenSerial: string, infoKey: string): Observable<Object> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete(`${this.tokenBaseUrl}info/` + tokenSerial + "/" + infoKey, {
        headers
      })
      .pipe(
        catchError((error) => {
          console.error("Failed to delete token info.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to delete token info. " + message);
          return throwError(() => error);
        })
      );
  }

  unassignUserFromAll(tokenSerials: string[]): Observable<PiResponse<boolean>[]> {
    if (tokenSerials.length === 0) {
      return new Observable<PiResponse<boolean>[]>((subscriber) => {
        subscriber.next([]);
        subscriber.complete();
      });
    }
    const observables = tokenSerials.map((tokenSerial) => this.unassignUser(tokenSerial));
    return forkJoin(observables).pipe(
      catchError((error) => {
        console.error("Failed to unassign user from all tokens.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to unassign user from all tokens. " + message);
        return throwError(() => error);
      })
    );
  }

  unassignUser(tokenSerial: string): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<boolean>>(`${this.tokenBaseUrl}unassign`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to unassign user.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to unassign user. " + message);
          return throwError(() => error);
        })
      );
  }

  assignUserToAll(args: {
    tokenSerials: string[];
    username: string;
    realm: string;
    pin?: string;
  }): Observable<PiResponse<boolean>[]> {
    const { tokenSerials, username, realm, pin } = args;
    const observables = tokenSerials.map((tokenSerial) =>
      this.assignUser({
        tokenSerial: tokenSerial,
        username: username,
        realm: realm,
        pin: pin || ""
      })
    );
    return forkJoin(observables).pipe(
      catchError((error) => {
        console.error("Failed to assign user to all tokens.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to assign user to all tokens. " + message);
        return throwError(() => error);
      })
    );
  }

  assignUser(args: {
    tokenSerial: string;
    username: string;
    realm: string;
    pin?: string;
  }): Observable<PiResponse<boolean>> {
    const { tokenSerial, username, realm, pin } = args;
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<boolean>>(
        `${this.tokenBaseUrl}assign`,
        {
          serial: tokenSerial,
          user: username !== "" ? username : null,
          realm: realm !== "" ? realm : null,
          pin: pin || ""
        },
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

  setPin(tokenSerial: string, userPin: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}setpin`,
        {
          serial: tokenSerial,
          otppin: userPin
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to set PIN.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set PIN. " + message);
          return throwError(() => error);
        })
      );
  }

  setRandomPin(tokenSerial: string): Observable<any> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}setrandompin`,
        {
          serial: tokenSerial
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to set random PIN.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set random PIN. " + message);
          return throwError(() => error);
        })
      );
  }

  resyncOTPToken(tokenSerial: string, fristOTPValue: string, secondOTPValue: string): Observable<Object> {
    const headers = this.authService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}resync`,
        {
          serial: tokenSerial,
          otp1: fristOTPValue,
          otp2: secondOTPValue
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to resync OTP token.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to resync OTP token. " + message);
          return throwError(() => error);
        })
      );
  }

  setTokenRealm(tokenSerial: string, value: string[]): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();

    return this.http
      .post<PiResponse<boolean>>(
        `${this.tokenBaseUrl}realm/` + tokenSerial,
        {
          realms: value
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to set token realm.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set token realm. " + message);
          return throwError(() => error);
        })
      );
  }

  setTokengroup(tokenSerial: string, value: string | string[]): Observable<Object> {
    const headers = this.authService.getHeaders();

    const valueArray: string[] = Array.isArray(value)
      ? value
      : typeof value === "object" && value !== null
        ? Object.values(value)
        : [value];
    return this.http
      .post(
        `${this.tokenBaseUrl}group/` + tokenSerial,
        {
          groups: valueArray
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to set token group.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set token group. " + message);
          return throwError(() => error);
        })
      );
  }

  lostToken(tokenSerial: string): Observable<LostTokenResponse> {
    const headers = this.authService.getHeaders();
    return this.http.post<LostTokenResponse>(`${this.tokenBaseUrl}lost/` + tokenSerial, {}, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to mark token as lost.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to mark token as lost. " + message);
        return throwError(() => error);
      })
    );
  }

  enrollToken<T extends TokenEnrollmentData, R extends EnrollmentResponse>(args: {
    data: T;
    mapper: TokenApiPayloadMapper<T>;
  }): Observable<R> {
    const { data, mapper } = args;
    const headers = this.authService.getHeaders();
    const params = mapper.toApiPayload(data);

    return this.http
      .post<R>(`${this.tokenBaseUrl}init`, params, {
        headers
      })
      .pipe(
        catchError((error) => {
          console.error("Failed to enroll token.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to enroll token. " + message);
          return throwError(() => error);
        })
      );
  }

  getTokenDetails(tokenSerial: string): Observable<PiResponse<Tokens>> {
    const headers = this.authService.getHeaders();
    let params = new HttpParams().set("serial", tokenSerial);
    return this.http.get<PiResponse<Tokens>>(this.tokenBaseUrl, {
      headers,
      params
    });
  }

  getTokengroups(): Observable<PiResponse<TokenGroups>> {
    const headers = this.authService.getHeaders();
    return this.http.get<PiResponse<TokenGroups>>(environment.proxyUrl + `/tokengroup/`, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to get token groups.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to get tokengroups. " + message);
        return throwError(() => error);
      })
    );
  }

  getSerial(
    otp: string,
    params: HttpParams
  ): Observable<PiResponse<{ count: number; serial?: string | undefined }, unknown>> {
    const headers = this.authService.getHeaders();
    return this.http
      .get<PiResponse<{ count: number; serial?: string }>>(`${this.tokenBaseUrl}getserial/${otp}`, {
        params: params,
        headers: headers
      })
      .pipe(
        catchError((error) => {
          console.error("Failed to get count.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to get count. " + message);
          return throwError(() => error);
        })
      );
  }

  pollTokenRolloutState(args: { tokenSerial: string; initDelay: number }): Observable<PiResponse<Tokens>> {
    const { tokenSerial, initDelay } = args;
    this.tokenSerial.set(tokenSerial);
    return timer(initDelay, 2000).pipe(
      takeUntil(this.stopPolling$),
      switchMap(() => {
        return this.getTokenDetails(this.tokenSerial());
      }),
      takeWhile((response: any) => response.result?.value.tokens[0].rollout_state === "clientwait", true),
      catchError((error) => {
        console.error("Failed to poll token state.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to poll token state. " + message);
        return throwError(() => error);
      }),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  stopPolling(): void {
    this.stopPolling$.next();
  }
}
