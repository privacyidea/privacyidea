import {
  HttpClient,
  HttpErrorResponse,
  HttpParams,
  httpResource,
  HttpResourceRef,
} from '@angular/common/http';
import {
  computed,
  effect,
  Injectable,
  linkedSignal,
  Signal,
  signal,
  WritableSignal,
} from '@angular/core';
import { Sort } from '@angular/material/sort';
import {
  forkJoin,
  Observable,
  Subject,
  switchMap,
  throwError,
  timer,
} from 'rxjs';
import { catchError, shareReplay, takeUntil, takeWhile } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import {
  TokenComponent,
  TokenTypeOption as TokenTypeKey,
} from '../../components/token/token.component';
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData,
} from '../../mappers/token-api-payload/_token-api-payload.mapper';
import { ContentService } from '../content/content.service';
import { LocalService } from '../local/local.service';
import { NotificationService } from '../notification/notification.service';

const apiFilter = [
  'serial',
  'type',
  'active',
  'description',
  'rollout_state',
  'user',
  'tokenrealm',
  'container_serial',
];
const advancedApiFilter = [
  'infokey & infovalue',
  'userid',
  'resolver',
  'assigned',
];
const hiddenApiFilter = ['type_list'];

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

export interface TokenServiceInterface {
  stopPolling$: Subject<void>;
  tokenBaseUrl: string;
  eventPageSize: number;
  selectedContent: Signal<string>;
  tokenSerial: Signal<string>;
  selectedTokenType: Signal<TokenType>;
  showOnlyTokenNotInContainer: WritableSignal<boolean>;
  filterValue: WritableSignal<Record<string, string>>;
  tokenDetailResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  tokenTypesResource: HttpResourceRef<PiResponse<{}> | undefined>;
  tokenTypeOptions: Signal<TokenType[]>;
  pageSize: WritableSignal<number>;

  sort: WritableSignal<Sort>;
  pageIndex: WritableSignal<number>;
  filterParams: Signal<Record<string, string>>;
  tokenResource: HttpResourceRef<PiResponse<Tokens> | undefined>;
  tokenSelection: WritableSignal<TokenDetails[]>;
  toggleActive(
    tokenSerial: string,
    active: boolean,
  ): Observable<PiResponse<boolean>>;
  resetFailCount(tokenSerial: string): Observable<PiResponse<boolean>>;
  saveTokenDetail(
    tokenSerial: string,
    key: string,
    value: any,
  ): Observable<PiResponse<boolean>>;

  setTokenInfos(
    tokenSerial: string,
    infos: any,
  ): Observable<PiResponse<boolean>[]>;

  deleteToken(tokenSerial: string): Observable<Object>;

  deleteTokens(tokenSerials: string[]): Observable<Object[]>;

  revokeToken(tokenSerial: string): Observable<any>;

  deleteInfo(tokenSerial: string, infoKey: string): Observable<Object>;
  unassignUserFromAll(
    tokenSerials: string[],
  ): Observable<PiResponse<boolean>[]>;

  unassignUser(tokenSerial: string): Observable<PiResponse<boolean>>;

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
    pin: string;
  }): Observable<PiResponse<boolean>>;

  setPin(tokenSerial: string, userPin: string): Observable<any>;
  setRandomPin(tokenSerial: string): Observable<any>;
}

@Injectable({
  providedIn: 'root',
})
export class TokenService implements TokenServiceInterface {
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  readonly hiddenApiFilter = hiddenApiFilter;
  readonly defaultSizeOptions = [5, 10, 25, 50];

  tokenBaseUrl = environment.proxyUrl + '/token/';
  eventPageSize = 10;
  stopPolling$ = new Subject<void>();
  tokenIsActive = signal(true);
  tokenIsRevoked = signal(true);
  tokenSerial = this.contentService.tokenSerial;
  selectedContent = this.contentService.selectedContent;
  showOnlyTokenNotInContainer = linkedSignal({
    source: this.contentService.selectedContent,
    computation: (selectedContent) => {
      return selectedContent === 'container_details';
    },
  });
  filterValue: WritableSignal<Record<string, string>> = linkedSignal({
    source: () => ({
      showOnlyTokenNotInContainer: this.showOnlyTokenNotInContainer(),
      selectedContent: this.contentService.selectedContent(),
    }),
    computation: (source, previous) => {
      switch (source.selectedContent) {
        case 'container_details':
          if (
            !previous ||
            source.selectedContent !== previous.source.selectedContent
          ) {
            return { container_serial: '' };
          } else {
            const current = { ...previous.value };
            if (source.showOnlyTokenNotInContainer) {
              current['container_serial'] = '';
            } else {
              delete current['container_serial'];
            }
            return current;
          }
        default:
          return {};
      }
    },
  });
  tokenDetailResource = httpResource<PiResponse<Tokens>>(() => {
    if (this.selectedContent() !== 'token_details') {
      return undefined;
    }
    return {
      url: this.tokenBaseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: { serial: this.tokenSerial() },
    };
  });
  tokenTypesResource = httpResource<PiResponse<{}>>(() => ({
    url: environment.proxyUrl + '/auth/rights',
    method: 'GET',
    headers: this.localService.getHeaders(),
  }));
  tokenTypeOptions = computed<TokenType[]>(() => {
    const obj = this.tokenTypesResource?.value()?.result?.value;
    if (!obj) return [];
    return Object.entries(obj).map(([key, info]) => ({
      key: key as TokenTypeKey,
      info: String(info),
      text:
        TokenComponent.tokenTypeTexts.find((t) => t.key === key)?.text || '',
    }));
  });
  selectedTokenType = linkedSignal({
    source: () => ({
      tokenTypeOptions: this.tokenTypeOptions(),
      selectedContent: this.contentService.selectedContent(),
    }),
    computation: (source) =>
      source.tokenTypeOptions.find((type) => type.key === 'hotp') ||
      source.tokenTypeOptions[0],
  });
  pageSize = linkedSignal<Record<string, string>, number>({
    source: this.filterValue,
    computation: (_, previous) => {
      const previousValue = previous?.value ?? 10;

      if (!this.defaultSizeOptions.includes(previousValue)) {
        return (
          this.defaultSizeOptions
            .slice()
            .reverse()
            .find((size) => size <= previousValue) ?? 10
        );
      }
      return previousValue;
    },
  });
  sort = linkedSignal({
    source: () => ({
      pageSize: this.pageSize(),
      selectedContent: this.contentService.selectedContent(),
    }),
    computation: () => {
      return { active: 'serial', direction: 'asc' } as Sort;
    },
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize(),
      selectedContent: this.contentService.selectedContent(),
      sort: this.sort(),
    }),
    computation: () => 0,
  });
  filterParams = computed<Record<string, string>>(() => {
    const allowedFilters = [
      ...this.apiFilter,
      ...this.advancedApiFilter,
      ...this.hiddenApiFilter,
    ];
    const filterPairs = Object.entries(this.filterValue())
      .filter(([key]) => allowedFilters.includes(key))
      .map(([key, value]) => ({ key, value }));

    return filterPairs.reduce(
      (acc, { key, value }) => ({
        ...acc,
        [key]: [
          'user',
          'infokey',
          'infovalue',
          'active',
          'assigned',
          'container_serial',
        ].includes(key)
          ? `${value}`
          : `*${value}*`,
      }),
      {} as Record<string, string>,
    );
  });
  tokenResource = httpResource<PiResponse<Tokens>>(() => {
    if (
      this.selectedContent() !== 'token_overview' &&
      this.selectedContent() !== 'container_details' &&
      this.selectedContent() !== 'token_self-service_menu'
    ) {
      return undefined;
    }
    return {
      url: this.tokenBaseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: {
        page: this.pageIndex() + 1,
        pagesize: this.pageSize(),
        sortby: this.sort()?.active || 'serial',
        sortdir: this.sort()?.direction || 'asc',
        ...this.filterParams(),
      },
    };
  });

  tokenSelection: WritableSignal<TokenDetails[]> = linkedSignal({
    source: () => ({
      selectedContent: this.contentService.selectedContent(),
      tokenResource: this.tokenResource.value(),
    }),
    computation: () => [],
  });

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private notificationService: NotificationService,
    private contentService: ContentService,
  ) {
    effect(() => {
      if (this.tokenResource.error()) {
        let tokensResourceError =
          this.tokenResource.error() as HttpErrorResponse;
        console.error('Failed to get token data.', tokensResourceError.message);
        this.notificationService.openSnackBar(tokensResourceError.message);
      }
    });
    effect(() => {
      if (this.tokenTypesResource.error()) {
        let tokenTypesResourceError =
          this.tokenTypesResource.error() as HttpErrorResponse;
        console.error(
          'Failed to get token type data.',
          tokenTypesResourceError.message,
        );
        this.notificationService.openSnackBar(tokenTypesResourceError.message);
      }
    });
  }

  toggleActive(tokenSerial: string, active: boolean) {
    const headers = this.localService.getHeaders();
    const action = active ? 'disable' : 'enable';
    return this.http
      .post<
        PiResponse<boolean>
      >(`${this.tokenBaseUrl}${action}`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to toggle active.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to toggle active. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  resetFailCount(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post<
        PiResponse<boolean>
      >(this.tokenBaseUrl + 'reset', { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to reset fail count.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to reset fail count. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  saveTokenDetail(tokenSerial: string, key: string, value: any) {
    const headers = this.localService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;

    const params =
      key === 'maxfail'
        ? { serial: tokenSerial, max_failcount: value }
        : { serial: tokenSerial, [key]: value };

    return this.http
      .post<PiResponse<boolean>>(set_url, params, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to set token detail.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set token detail. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setTokenInfos(tokenSerial: string, infos: any) {
    const headers = this.localService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;
    const info_url = `${this.tokenBaseUrl}info`;

    const postRequest = (url: string, body: any) => {
      return this.http.post<PiResponse<boolean>>(url, body, { headers }).pipe(
        catchError((error) => {
          console.error('Failed to set token info.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set token info. ' + message,
          );
          return throwError(() => error);
        }),
      );
    };

    const requests = Object.keys(infos).map((infoKey) => {
      const infoValue = infos[infoKey];
      if (
        infoKey === 'count_auth_max' ||
        infoKey === 'count_auth_success_max' ||
        infoKey === 'hashlib' ||
        infoKey === 'validity_period_start' ||
        infoKey === 'validity_period_end'
      ) {
        return postRequest(set_url, {
          serial: tokenSerial,
          [infoKey]: infoValue,
        });
      } else {
        return postRequest(`${info_url}/${tokenSerial}/${infoKey}`, {
          value: infoValue,
        });
      }
    });
    return forkJoin(requests);
  }

  deleteToken(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http.delete(this.tokenBaseUrl + tokenSerial, { headers });
  }

  deleteTokens(tokenSerials: string[]) {
    const headers = this.localService.getHeaders();
    const observables = tokenSerials.map((tokenSerial) =>
      this.deleteToken(tokenSerial),
    );
    return forkJoin(observables);
  }

  revokeToken(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(`${this.tokenBaseUrl}revoke`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to revoke token.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to revoke token. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  deleteInfo(tokenSerial: string, infoKey: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .delete(`${this.tokenBaseUrl}info/` + tokenSerial + '/' + infoKey, {
        headers,
      })
      .pipe(
        catchError((error) => {
          console.error('Failed to delete token info.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to delete token info. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  unassignUserFromAll(tokenSerials: string[]) {
    if (tokenSerials.length === 0) {
      return new Observable<PiResponse<boolean>[]>((subscriber) => {
        subscriber.next([]);
        subscriber.complete();
      });
    }
    const observables = tokenSerials.map((tokenSerial) =>
      this.unassignUser(tokenSerial),
    );
    return forkJoin(observables).pipe(
      catchError((error) => {
        console.error('Failed to unassign user from all tokens.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to unassign user from all tokens. ' + message,
        );
        return throwError(() => error);
      }),
    );
  }

  unassignUser(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post<
        PiResponse<boolean>
      >(`${this.tokenBaseUrl}unassign`, { serial: tokenSerial }, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to unassign user.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to unassign user. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  assignUserToAll(args: {
    tokenSerials: string[];
    username: string;
    realm: string;
    pin?: string;
  }) {
    const { tokenSerials, username, realm, pin } = args;
    var observables = tokenSerials.map((tokenSerial) =>
      this.assignUser({
        tokenSerial: tokenSerial,
        username: username,
        realm: realm,
        pin: pin || '',
      }),
    );
    return forkJoin(observables).pipe(
      catchError((error) => {
        console.error('Failed to assign user to all tokens.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to assign user to all tokens. ' + message,
        );
        return throwError(() => error);
      }),
    );
  }

  assignUser(args: {
    tokenSerial: string;
    username: string;
    realm: string;
    pin: string;
  }) {
    const { tokenSerial, username, realm, pin } = args;
    const headers = this.localService.getHeaders();
    return this.http
      .post<PiResponse<boolean>>(
        `${this.tokenBaseUrl}assign`,
        {
          serial: tokenSerial,
          user: username !== '' ? username : null,
          realm: realm !== '' ? realm : null,
          pin: pin,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to assign user.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to assign user. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setPin(tokenSerial: string, userPin: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}setpin`,
        {
          serial: tokenSerial,
          otppin: userPin,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to set PIN.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set PIN. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setRandomPin(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}setrandompin`,
        {
          serial: tokenSerial,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to set random PIN.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set random PIN. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  resyncOTPToken(
    tokenSerial: string,
    fristOTPValue: string,
    secondOTPValue: string,
  ) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}resync`,
        {
          serial: tokenSerial,
          otp1: fristOTPValue,
          otp2: secondOTPValue,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to resync OTP token.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to resync OTP token. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setTokenRealm(tokenSerial: string, value: string[]) {
    const headers = this.localService.getHeaders();
    return this.http
      .post<PiResponse<boolean>>(
        `${this.tokenBaseUrl}realm/` + tokenSerial,
        {
          realms: value,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to set token realm.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set token realm. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  setTokengroup(tokenSerial: string, value: string | string[]) {
    const headers = this.localService.getHeaders();
    const valueArray: string[] = Array.isArray(value)
      ? value
      : typeof value === 'object' && value !== null
        ? Object.values(value)
        : [value];
    return this.http
      .post(
        `${this.tokenBaseUrl}group/` + tokenSerial,
        {
          groups: valueArray,
        },
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to set token group.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to set token group. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  lostToken(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post<LostTokenResponse>(
        `${this.tokenBaseUrl}lost/` + tokenSerial,
        {},
        { headers },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to mark token as lost.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to mark token as lost. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  enrollToken<
    T extends TokenEnrollmentData,
    R extends EnrollmentResponse,
  >(args: { data: T; mapper: TokenApiPayloadMapper<T> }) {
    const { data, mapper } = args;
    const headers = this.localService.getHeaders();
    const params = mapper.toApiPayload(data);

    return this.http
      .post<R>(`${this.tokenBaseUrl}init`, params, {
        headers,
      })
      .pipe(
        catchError((error) => {
          console.error('Failed to enroll token.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to enroll token. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  getTokenDetails(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    let params = new HttpParams().set('serial', tokenSerial);
    return this.http.get<PiResponse<Tokens>>(this.tokenBaseUrl, {
      headers,
      params,
    });
  }

  getTokengroups() {
    const headers = this.localService.getHeaders();
    return this.http
      .get<
        PiResponse<TokenGroups>
      >(environment.proxyUrl + `/tokengroup/`, { headers })
      .pipe(
        catchError((error) => {
          console.error('Failed to get token groups.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to get tokengroups. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  getSerial(otp: string, params: HttpParams) {
    const headers = this.localService.getHeaders();
    return this.http
      .get<PiResponse<{ count: number; serial?: string }>>(
        `${this.tokenBaseUrl}getserial/${otp}`,
        {
          params: params,
          headers: headers,
        },
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to get count.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to get count. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }

  pollTokenRolloutState(args: {
    tokenSerial: string;
    initDelay: number;
  }): Observable<PiResponse<Tokens>> {
    const { tokenSerial, initDelay } = args;
    this.tokenSerial.set(tokenSerial);
    return timer(initDelay, 2000).pipe(
      takeUntil(this.stopPolling$),
      switchMap(() => {
        return this.getTokenDetails(this.tokenSerial());
      }),
      takeWhile(
        (response: any) =>
          response.result?.value.tokens[0].rollout_state === 'clientwait',
        true,
      ),
      catchError((error) => {
        console.error('Failed to poll token state.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to poll token state. ' + message,
        );
        return throwError(() => error);
      }),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }

  stopPolling() {
    this.stopPolling$.next();
  }
}
