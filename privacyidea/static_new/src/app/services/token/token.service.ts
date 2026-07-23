/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { PiResponse } from "@app/app.component";
import {
  BaseApiPayloadMapper,
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface, DetailsUser } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { parseBooleanValue } from "@utils/parse-boolean-value";
import { StringUtils } from "@utils/string.utils";
import { FilterCaseNote } from "@utils/filter-hint.utils";
import { tokenTypes } from "@utils/token.utils";
import {
  catchError,
  firstValueFrom,
  forkJoin,
  Observable,
  shareReplay,
  Subject,
  switchMap,
  takeUntil,
  takeWhile,
  throwError,
  timer
} from "rxjs";

export type TokenTypeKey =
  | "hotp"
  | "totp"
  | "spass"
  | "motp"
  | "sshkey"
  | "yubikey"
  | "remote"
  | "yubico"
  | "radius"
  | "sms"
  | "4eyes"
  | "applspec"
  | "certificate"
  | "daypassword"
  | "email"
  | "indexedsecret"
  | "paper"
  | "push"
  | "question"
  | "registration"
  | "tan"
  | "tiqr"
  | "u2f"
  | "vasco"
  | "webauthn"
  | "passkey";

const apiFilter = [
  "serial",
  "type",
  "active",
  "user",
  "realm",
  "description",
  "rollout_state",
  "tokenrealm",
  "container_serial"
];

const advancedApiFilter = ["infokey & infovalue", "userid", "resolver", "assigned"];

const apiFilterKeyMap: Record<string, string> = {
  serial: "serial",
  tokentype: "type",
  active: "active",
  description: "description",
  rollout_state: "rollout_state",
  username: "user",
  realms: "tokenrealm",
  user_realm: "realm",
  container_serial: "container_serial"
};

const hiddenApiFilter = ["type_list"];

const exactMatchKeys = new Set([
  "user",
  "infokey",
  "infovalue",
  "infokey & infovalue",
  "active",
  "assigned",
  "container_serial",
  "realm"
]);
const booleanKeys = new Set(["active", "assigned"]);
// `serial` is a raw LIKE (SQLite/MySQL fold case, PostgreSQL does not), the tokeninfo
// keys are a raw equality comparison (only MySQL with a _ci collation folds case).
const caseNotes: Record<string, FilterCaseNote> = {
  serial: "usually-insensitive",
  "infokey & infovalue": "usually-sensitive"
};
// TODO: temporary. The backend accepts these keywords but never applies them, because
// the filter clauses were removed in 78c0cc621 and not restored. Once they either work
// again or are dropped, remove this set along with the whole "unsupported" mechanism.
const unsupportedKeys = new Set(["userid", "resolver"]);

export interface Tokens {
  count: number;
  current: number;
  next?: number;
  page?: number;
  tokens: TokenDetails[];
}

export type TokenCount = Pick<Tokens, "count">;

export interface TokenCountParams {
  type?: TokenTypeKey;
  type_list?: string;
  serial?: string;
  description?: string;
  assigned?: "True" | "False";
  active?: "True" | "False";
  rollout_state?: string;
  infokey?: string;
  infovalue?: string;
  container_serial?: string;
  tokenrealm?: string;
  realm?: string;
  user?: string;
  userid?: string;
  resolver?: string;
}

export interface TokenInfo {
  CA?: string;
  dynamic_email?: string;
  dynamic_phone?: string;
  email?: string;
  hashlib?: string;
  phone?: string;
  pin?: string;
  rollover?: string;
  separator?: string;
  service_id?: string;
  timeStep?: string;
  validity_period_end?: string;
  validity_period_start?: string;

  [key: string]: string | undefined;
}

export interface TokenDetails {
  active: boolean;
  container_serial: string;
  count: number;
  count_window: number;
  description: string;
  failcount: number;
  id: number;
  info: TokenInfo;
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
  name: string;
  info: string;
  text: string;
  rollover?: boolean;
}

export interface WebAuthnRegisterRequest {
  attestation: string;
  authenticatorSelection: AuthenticatorSelectionCriteria;
  displayName: string;
  message: string;
  name: string;
  nonce: string;
  excludeCredentials?: { id: string; type: string; transports?: string[] }[];
  extensions?: Record<string, unknown>;
  pubKeyCredAlgorithms: PublicKeyCredentialParameters[];
  relyingParty: {
    id: string;
    name: string;
  };
  serialNumber: string;
  timeout: number;
  transaction_id: string;
}

export type LostTokenResponse = PiResponse<LostTokenData>;

export interface EnrollTokenArguments {
  data: TokenEnrollmentData;
  mapper: BaseApiPayloadMapper;
}

export interface TokenEnrollmentDialogData {
  tokenType: string;
  response: EnrollmentResponse | null;
  enrollParameters: EnrollTokenArguments;
  username?: string;
  userRealm?: string;
  onlyAddToRealm?: boolean;
  rollover?: boolean;
  showEnrollData?: boolean;
}

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

export interface TokenImportResult {
  n_imported: number;
  n_not_imported: number;
}

export interface TokenServiceInterface {
  apiFilterKeyMap: Record<string, string>;
  stopPolling$: Subject<void>;
  tokenBaseUrl: string;
  eventPageSize: WritableSignal<number>;
  tokenSerial: WritableSignal<string>;
  selectedTokenType: WritableSignal<TokenType>;
  showOnlyTokenInContainer: WritableSignal<boolean>;
  tokenFilter: WritableSignal<FilterValue>;
  presetFilter: WritableSignal<FilterValue | null>;
  tokenDetailResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  tokenDetailResourceValue: Signal<Tokens | undefined>;
  tokenTypesResource: HttpResourceRef<PiResponse<Record<string, string>> | undefined>;
  userTokenResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  detailsUser: WritableSignal<DetailsUser>;
  tokenTypeOptions: Signal<TokenType[]>;
  pageSize: WritableSignal<number>;
  tokenIsActive: WritableSignal<boolean>;
  tokenIsRevoked: WritableSignal<boolean>;
  defaultSizeOptions: number[];
  apiFilter: string[];
  advancedApiFilter: string[];
  exactMatchKeys: Set<string>;
  booleanKeys: Set<string>;
  caseNotes: Record<string, FilterCaseNote>;
  unsupportedKeys: Set<string>;
  sort: WritableSignal<Sort>;
  pageIndex: WritableSignal<number>;
  tokenResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  tokenSerialResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  tokenResourceValue: Signal<Tokens | null>;
  tokenSelection: WritableSignal<TokenDetails[]>;
  selectedToken: WritableSignal<string | null>;
  tokenOptions: Signal<string[]>;
  filteredTokenOptions: Signal<string[]>;
  readonly maxDescriptionLength: number;

  clearFilter(): void;

  handleFilterInput($event: Event): void;

  toggleActive(tokenSerial: string, active: boolean, notify?: boolean): Observable<PiResponse<boolean>>;

  resetFailCount(tokenSerial: string, notify?: boolean): Observable<PiResponse<boolean>>;

  saveTokenDetail(tokenSerial: string, key: string, value: unknown): Observable<PiResponse<boolean>>;

  getSerial(otp: string, params: HttpParams): Observable<PiResponse<{ count: number; serial?: string | undefined }>>;

  setTokenInfos(tokenSerial: string, infos: Record<string, string>): Observable<PiResponse<boolean>[]>;

  deleteToken(tokenSerial: string): Observable<PiResponse<number>>;

  bulkDeleteTokens(selectedTokens: string[]): Observable<PiResponse<BulkResult>>;

  bulkDeleteWithConfirmDialog(serialList: string[], afterDelete?: () => void): void;

  revokeToken(tokenSerial: string): Observable<PiResponse<number>>;

  deleteInfo(tokenSerial: string, infoKey: string): Observable<PiResponse<boolean>>;

  unassignUserFromAll(tokenSerials: string[]): Observable<PiResponse<boolean>[]>;

  unassignUser(tokenSerial: string, notify?: boolean): Observable<PiResponse<boolean>>;

  bulkUnassignTokens(tokenDetails: TokenDetails[]): Observable<PiResponse<BulkResult>>;

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

  setPin(tokenSerial: string, userPin: string): Observable<PiResponse<number>>;

  setRandomPin(tokenSerial: string): Observable<PiResponse<number, { pin: string }>>;

  resyncOTPToken(tokenSerial: string, firstOTPValue: string, secondOTPValue: string): Promise<PiResponse<boolean>>;

  getTokenDetails(tokenSerial: string): Observable<PiResponse<Tokens>>;

  getTokenCount(params?: TokenCountParams): Observable<PiResponse<TokenCount>>;

  enrollToken<T extends TokenEnrollmentData, R extends EnrollmentResponse>(args: {
    data: T;
    mapper: TokenApiPayloadMapper<T>;
  }): Observable<R>;

  verifyToken(verifyData: TokenEnrollmentData): Observable<PiResponse<boolean, EnrollmentResponseDetail>>;

  lostToken(tokenSerial: string): Observable<LostTokenResponse>;

  stopPolling(): void;

  pollTokenRolloutState(args: { tokenSerial: string; initDelay: number }): Observable<PiResponse<Tokens>>;

  setTokenRealm(tokenSerial: string, value: string[]): Observable<PiResponse<boolean>>;

  getTokengroups(): Observable<PiResponse<TokenGroups>>;

  setTokengroup(tokenSerial: string, value: string | string[]): Observable<PiResponse<number>>;

  importTokens(fileName: string, params: FormData): Observable<PiResponse<TokenImportResult>>;
}

@Injectable()
export class TokenService implements TokenServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly http = inject(HttpClient);
  readonly hiddenApiFilter = hiddenApiFilter;
  readonly apiFilterKeyMap = apiFilterKeyMap;
  readonly stopPolling$ = new Subject<void>();
  readonly tokenBaseUrl = environment.proxyUrl + "/token/";
  readonly eventPageSize = signal(10);
  readonly tokenSerial = this.contentService.tokenSerial;
  private readonly _filterParams = computed<Record<string, string>>(() => {
    const allowed = [...this.apiFilter, ...this.advancedApiFilter, ...this.hiddenApiFilter, "infokey", "infovalue"];
    const plainKeys = exactMatchKeys;
    const entries = [
      ...Array.from(this.tokenFilter().filterMap.entries()),
      ...Array.from(this.tokenFilter().hiddenFilterMap.entries())
    ]
      .filter(([key]) => allowed.includes(key))
      .map(([key, value]) => [key, (value ?? "").toString().trim()] as const)
      .filter(([key, v]) => (key === "container_serial" ? true : StringUtils.validFilterValue(v)))
      .map(([key, v]) => {
        if (key === "active" || key === "assigned") {
          const lower = v.toLowerCase();
          if (lower === "true" || lower === "1" || lower === "false" || lower === "0") {
            return [key, parseBooleanValue(v) ? "True" : "False"] as const;
          }
          return [key, v] as const;
        }
        return [key, plainKeys.has(key) ? v : `*${v}*`] as const;
      });
    return Object.fromEntries(entries) as Record<string, string>;
  });

  constructor() {
    effect(() => {
      if (this.tokenResource.error()) {
        const tokensResourceError = this.tokenResource.error() as HttpErrorResponse;
        console.error("Failed to get token data.", tokensResourceError.error.result.error.message);
        this.notificationService.error(tokensResourceError.error.result.error.message);
      }
    });
    effect(() => {
      if (this.tokenTypesResource.error()) {
        const tokenTypesResourceError = this.tokenTypesResource.error() as HttpErrorResponse;
        console.error("Failed to get token type data.", tokenTypesResourceError.error.result.error.message);
        this.notificationService.error(tokenTypesResourceError.error.result.error.message);
      }
    });
  }

  readonly maxDescriptionLength = 80;

  readonly detailsUser = this.contentService.detailsUser;

  tokenSerialResource = httpResource<PiResponse<Tokens>>(() => {
    const filter = this.selectedToken();
    if (!filter || filter.length < 1) {
      return undefined;
    }
    return {
      url: this.tokenBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: { serial: `*${filter}*` }
    };
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

  showOnlyTokenInContainer = linkedSignal({
    source: this.contentService.routeUrl,
    computation: () => {
      // Initially hide tokens that are already in a container (i.e. show only
      // free tokens) on the container details route.
      return !this.contentService.onContainersDetails();
    }
  });

  presetFilter: WritableSignal<FilterValue | null> = signal<FilterValue | null>(null);
  tokenFilter: WritableSignal<FilterValue> = linkedSignal({
    source: () => ({
      showOnlyTokenInContainer: this.showOnlyTokenInContainer(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: (source, previous) => {
      // Outside of container details and user details we reset the filter.
      if (!this.contentService.onContainersDetails() && !this.contentService.onUserDetails()) {
        return new FilterValue();
      }
      // Initialize filter when the route changes.
      if (!previous || source.routeUrl !== previous.source.routeUrl) {
        let filterValue = new FilterValue({
          hiddenValue: this.contentService.onContainersDetails()
            ? source.showOnlyTokenInContainer
              ? " "
              : "container_serial:"
            : ""
        });

        if (this.contentService.onUserDetails()) {
          filterValue = filterValue.updateHiddenEntry("assigned", "false");
        }
        return filterValue;
      }

      let filterValue = previous.value;

      if (this.contentService.onContainersDetails()) {
        filterValue = source.showOnlyTokenInContainer
          ? filterValue.removeHiddenKey("container_serial")
          : filterValue.addHiddenKey("container_serial");
      } else {
        filterValue = filterValue.removeHiddenKey("container_serial");
      }

      if (this.contentService.onUserDetails()) {
        filterValue = filterValue.updateHiddenEntry("assigned", "false");
      } else {
        filterValue = filterValue.removeHiddenKey("assigned");
      }
      return filterValue;
    }
  });

  clearFilter(): void {
    this.tokenFilter.set(new FilterValue());
  }

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    let newFilter = this.tokenFilter().copyWith({ value: input.value.trim() });

    if (newFilter.hasKey("user") && !newFilter.hasKey("realm")) {
      const defaultRealm = this.realmService.defaultRealm();
      if (defaultRealm) {
        newFilter = newFilter.addEntry("realm", defaultRealm);
      }
    }

    this.tokenFilter.set(newFilter);
  }

  tokenDetailResource = httpResource<PiResponse<Tokens>>(() => {
    // Only load token details on the token details page.
    if (!this.contentService.onTokenDetails()) {
      return undefined;
    }

    return {
      url: this.tokenBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: { serial: this.tokenSerial() }
    };
  });

  tokenDetailResourceValue = computed(() => {
    if (!this.tokenDetailResource.hasValue()) return undefined;
    return this.tokenDetailResource.value()?.result?.value;
  });

  tokenTypesResource = httpResource<PiResponse<Record<string, string>>>(() => {
    // Only load token types on routes with a tokentype list or selection.
    const onAllowedRoute =
      this.contentService.onTokens() ||
      this.contentService.onTokensEnrollment() ||
      this.contentService.onTokensGetSerial() ||
      this.contentService.onContainersCreate() ||
      this.contentService.onContainersDetails() ||
      this.contentService.onUserDetails();

    if (!onAllowedRoute) {
      return undefined;
    }

    return {
      url: environment.proxyUrl + "/auth/rights",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  userTokenResource = httpResource<PiResponse<Tokens> | undefined>(() => {
    // Only load user tokens on the user details page.
    if (!this.contentService.onUserDetails()) {
      return undefined;
    }

    return {
      url: this.tokenBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: { user: this.detailsUser().username, realm: this.detailsUser().realm }
    };
  });

  tokenTypeOptions = computed<TokenType[]>(() => {
    if (!this.tokenTypesResource.hasValue()) return [];
    const obj = this.tokenTypesResource?.value()?.result?.value;
    if (!obj) return [];
    return Object.entries(obj).map(([key, info]) => ({
      key: key as TokenTypeKey,
      name: tokenTypes.find((t) => t.key === key)?.name || key,
      info: String(info),
      text: tokenTypes.find((t) => t.key === key)?.text || ""
    }));
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

  tokenIsActive = signal(true);
  tokenIsRevoked = signal(true);
  readonly defaultSizeOptions = [5, 10, 25, 50];
  readonly apiFilter = apiFilter;
  readonly exactMatchKeys = exactMatchKeys;
  readonly booleanKeys = booleanKeys;
  readonly caseNotes = caseNotes;
  readonly unsupportedKeys = unsupportedKeys;
  readonly advancedApiFilter = advancedApiFilter;

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

  tokenResource = httpResource<PiResponse<Tokens>>(() => {
    // Only load tokens on routes with a token list or selection.
    const onAllowedRoute =
      this.contentService.onTokens() ||
      this.contentService.onContainersDetails() ||
      this.contentService.onUserDetails();

    if (!onAllowedRoute) {
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
        ...this._filterParams()
      }
    };
  });

  tokenResourceValue = computed(() => {
    if (!this.tokenResource.hasValue()) return null;
    return this.tokenResource.value()?.result?.value || null;
  });

  tokenSelection: WritableSignal<TokenDetails[]> = linkedSignal({
    source: () => ({
      routeUrl: this.contentService.routeUrl(),
      tokenResource: this.tokenResourceValue()
    }),
    computation: () => []
  });

  selectedToken = signal<string | null>(null);

  tokenOptions: WritableSignal<string[]> = linkedSignal({
    source: () => ({
      value: this.tokenSerialResource.hasValue() ? this.tokenSerialResource.value() : undefined,
      isLoading: this.tokenSerialResource.isLoading(),
      error: this.tokenSerialResource.error()
    }),
    computation: (source, previous): string[] => {
      if (source.error) return [];
      if (!source.value) return source.isLoading ? (previous?.value ?? []) : [];
      return source.value.result?.value?.tokens?.map((token) => token.serial) ?? [];
    }
  });

  filteredTokenOptions = computed(() => {
    const filter = (this.selectedToken() || "").toLowerCase();
    return this.tokenOptions().filter((option) => option.toLowerCase().includes(filter));
  });

  bulkUnassignTokens(tokenDetails: TokenDetails[]): Observable<PiResponse<BulkResult>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<BulkResult>>(
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
          this.notificationService.error("Failed to unassign tokens. " + message);
          return throwError(() => error);
        })
      );
  }

  bulkDeleteTokens(selectedTokens: string[]): Observable<PiResponse<BulkResult>> {
    const headers = this.authService.getHeaders();
    const body = { serials: selectedTokens };

    return this.http.delete<PiResponse<BulkResult>>(this.tokenBaseUrl, { headers, body }).pipe(
      catchError((error) => {
        console.error("Failed to delete tokens.", error);
        const message = error.result?.error?.message || "";
        this.notificationService.error("Failed to delete tokens. " + message);
        return throwError(() => error);
      })
    );
  }

  bulkDeleteWithConfirmDialog(serialList: string[], afterDelete?: () => void) {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Delete Selected Tokens",
          items: serialList,
          itemType: "token",
          confirmAction: {
            type: "destruct",
            label: $localize`Delete`,
            value: true
          }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (!result) {
            return;
          }
          this.bulkDeleteTokens(serialList).subscribe({
            next: (response: PiResponse<BulkResult>) => {
              const failedTokens = response.result?.value?.failed || [];
              const unauthorizedTokens = response.result?.value?.unauthorized || [];
              const count_success = response.result?.value?.count_success || 0;
              const messages: string[] = [];
              if (count_success) {
                messages.push(`Successfully deleted ${count_success} token${count_success === 1 ? "" : "s"}.`);
              }

              if (failedTokens.length > 0) {
                messages.push(`The following tokens failed to delete: ${failedTokens.join(", ")}`);
              }

              if (unauthorizedTokens.length > 0) {
                messages.push(
                  `You are not authorized to delete the following tokens: ${unauthorizedTokens.join(", ")}`
                );
              }

              if (messages.length > 0) {
                this.notificationService.success(messages.join("\n"));
              }

              if (afterDelete) {
                afterDelete();
              }
            },
            error: (err) => {
              let message = "An error occurred while deleting tokens.";
              if (err.error?.result?.error?.message) {
                message = err.error.result.error.message;
              }
              this.notificationService.error(message);
            }
          });
        }
      });
  }

  toggleActive(tokenSerial: string, active: boolean, notify = true): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    const action = active ? "disable" : "enable";
    return this.http
      .post<PiResponse<boolean>>(`${this.tokenBaseUrl}${action}`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to toggle active.", error);
          if (notify) {
            const message = error.error?.result?.error?.message || "";
            this.notificationService.error("Failed to toggle active. " + message);
          }
          return throwError(() => error);
        })
      );
  }

  resetFailCount(tokenSerial: string, notify = true): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    return this.http.post<PiResponse<boolean>>(this.tokenBaseUrl + "reset", { serial: tokenSerial }, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to reset fail count.", error);
        if (notify) {
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to reset fail count. " + message);
        }
        return throwError(() => error);
      })
    );
  }

  saveTokenDetail(tokenSerial: string, key: string, value: unknown): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();

    let url: string;
    let params: Record<string, unknown>;
    if (key === "description") {
      url = `${this.tokenBaseUrl}description/${encodeURIComponent(tokenSerial)}`;
      params = { description: value };
    } else if (key === "maxfail") {
      url = `${this.tokenBaseUrl}set`;
      params = { serial: tokenSerial, max_failcount: value };
    } else {
      url = `${this.tokenBaseUrl}set`;
      params = { serial: tokenSerial, [key]: value };
    }

    return this.http.post<PiResponse<boolean>>(url, params, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to set token detail.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error("Failed to set token detail. " + message);
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
      .get<PiResponse<{ count: number; serial?: string }>>(`${this.tokenBaseUrl}getserial/${encodeURIComponent(otp)}`, {
        params: params,
        headers: headers
      })
      .pipe(
        catchError((error) => {
          console.error("Failed to get count.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to get count. " + message);
          return throwError(() => error);
        })
      );
  }

  setTokenInfos(tokenSerial: string, infos: Record<string, string>): Observable<PiResponse<boolean>[]> {
    const headers = this.authService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;
    const info_url = `${this.tokenBaseUrl}info`;

    const postRequest = (url: string, body: Record<string, string>) => {
      return this.http.post<PiResponse<boolean>>(url, body, { headers }).pipe(
        catchError((error) => {
          console.error("Failed to set token info.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to set token info. " + message);
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
        return postRequest(`${info_url}/${encodeURIComponent(tokenSerial)}/${encodeURIComponent(infoKey)}`, {
          value: infoValue
        });
      }
    });
    return forkJoin(requests);
  }

  deleteToken(tokenSerial: string): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http.delete<PiResponse<number>>(this.tokenBaseUrl + encodeURIComponent(tokenSerial), { headers });
  }

  revokeToken(tokenSerial: string): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http.post<PiResponse<number>>(`${this.tokenBaseUrl}revoke`, { serial: tokenSerial }, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to revoke token.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error("Failed to revoke token. " + message);
        return throwError(() => error);
      })
    );
  }

  deleteInfo(tokenSerial: string, infoKey: string): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    return this.http
      .delete<PiResponse<boolean>>(
        `${this.tokenBaseUrl}info/${encodeURIComponent(tokenSerial)}/${encodeURIComponent(infoKey)}`,
        {
          headers
        }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to delete token info.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to delete token info. " + message);
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
        this.notificationService.error("Failed to unassign user from all tokens. " + message);
        return throwError(() => error);
      })
    );
  }

  unassignUser(tokenSerial: string, notify = true): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<boolean>>(`${this.tokenBaseUrl}unassign`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to unassign user.", error);
          if (notify) {
            const message = error.error?.result?.error?.message || "";
            this.notificationService.error("Failed to unassign user. " + message);
          }
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
        this.notificationService.error("Failed to assign user to all tokens. " + message);
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
          this.notificationService.error("Failed to assign user. " + message);
          return throwError(() => error);
        })
      );
  }

  setPin(tokenSerial: string, userPin: string): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<number>>(
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
          this.notificationService.error("Failed to set PIN. " + message);
          return throwError(() => error);
        })
      );
  }

  setRandomPin(tokenSerial: string): Observable<PiResponse<number, { pin: string }>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<number, { pin: string }>>(
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
          this.notificationService.error("Failed to set random PIN. " + message);
          return throwError(() => error);
        })
      );
  }

  resyncOTPToken(tokenSerial: string, fristOTPValue: string, secondOTPValue: string): Promise<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();
    const request = this.http
      .post<PiResponse<boolean>>(
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
          this.notificationService.error("Failed to resync OTP token. " + message);
          return throwError(() => error);
        })
      );
    return firstValueFrom(request);
  }

  getTokenDetails(tokenSerial: string): Observable<PiResponse<Tokens>> {
    const headers = this.authService.getHeaders();
    const params = new HttpParams().set("serial", tokenSerial);
    return this.http.get<PiResponse<Tokens>>(this.tokenBaseUrl, {
      headers,
      params
    });
  }

  getTokenCount(params: TokenCountParams = {}): Observable<PiResponse<TokenCount>> {
    return this.http.get<PiResponse<TokenCount>>(this.tokenBaseUrl, {
      headers: this.authService.getHeaders(),
      params: { ...params, pagesize: 0 }
    });
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
          this.notificationService.error("Failed to enroll token. " + message);
          return throwError(() => error);
        })
      );
  }

  verifyToken(verifyData: TokenEnrollmentData): Observable<PiResponse<boolean, EnrollmentResponseDetail>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<boolean, EnrollmentResponseDetail>>(`${this.tokenBaseUrl}init`, verifyData, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to verify token.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to verify token. " + message);
          return throwError(() => error);
        })
      );
  }

  lostToken(tokenSerial: string): Observable<LostTokenResponse> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<LostTokenResponse>(`${this.tokenBaseUrl}lost/${encodeURIComponent(tokenSerial)}`, {}, { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to mark token as lost.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to mark token as lost. " + message);
          return throwError(() => error);
        })
      );
  }

  stopPolling(): void {
    this.stopPolling$.next();
  }

  pollTokenRolloutState(args: { tokenSerial: string; initDelay: number }): Observable<PiResponse<Tokens>> {
    const { tokenSerial, initDelay } = args;
    this.tokenSerial.set(tokenSerial);
    return timer(initDelay, 2000).pipe(
      takeUntil(this.stopPolling$),
      switchMap(() => {
        return this.getTokenDetails(this.tokenSerial());
      }),
      takeWhile(
        (response: PiResponse<Tokens>) => response.result?.value?.tokens[0].rollout_state === "clientwait",
        true
      ),
      catchError((error) => {
        console.error("Failed to poll token state.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error("Failed to poll token state. " + message);
        return throwError(() => error);
      }),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  setTokenRealm(tokenSerial: string, value: string[]): Observable<PiResponse<boolean>> {
    const headers = this.authService.getHeaders();

    return this.http
      .post<PiResponse<boolean>>(
        `${this.tokenBaseUrl}realm/${encodeURIComponent(tokenSerial)}`,
        {
          realms: value
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to set token realm.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to set token realm. " + message);
          return throwError(() => error);
        })
      );
  }

  getTokengroups(): Observable<PiResponse<TokenGroups>> {
    const headers = this.authService.getHeaders();
    return this.http.get<PiResponse<TokenGroups>>(environment.proxyUrl + `/tokengroup/`, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to get token groups.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error("Failed to get tokengroups. " + message);
        return throwError(() => error);
      })
    );
  }

  setTokengroup(tokenSerial: string, value: string | string[]): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();

    const valueArray: string[] = Array.isArray(value) ? value : [value];
    return this.http
      .post<PiResponse<number>>(
        `${this.tokenBaseUrl}group/${encodeURIComponent(tokenSerial)}`,
        {
          groups: valueArray
        },
        { headers }
      )
      .pipe(
        catchError((error) => {
          console.error("Failed to set token group.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to set token group. " + message);
          return throwError(() => error);
        })
      );
  }

  importTokens(fileName: string, params: FormData): Observable<PiResponse<TokenImportResult>> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<PiResponse<TokenImportResult>>(`${this.tokenBaseUrl}load/${encodeURIComponent(fileName)}`, params, {
        headers: headers
      })
      .pipe(
        catchError((error) => {
          console.error("Failed to import tokens.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to import tokens. " + message);
          return throwError(() => error);
        })
      );
  }
}
