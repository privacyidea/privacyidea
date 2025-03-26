import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import {
  forkJoin,
  Observable,
  Subject,
  switchMap,
  takeUntil,
  takeWhile,
  throwError,
  timer,
} from 'rxjs';
import { LocalService } from '../local/local.service';
import { Sort } from '@angular/material/sort';
import { TableUtilsService } from '../table-utils/table-utils.service';
import { environment } from '../../../environments/environment';
import { catchError } from 'rxjs/operators';
import { NotificationService } from '../notification/notification.service';

@Injectable({
  providedIn: 'root',
})
export class TokenService {
  apiFilter = [
    'serial',
    'type',
    'active',
    'description',
    'rollout_state',
    'user',
    'tokenrealm',
    'container_serial',
  ];
  advancedApiFilter = ['infokey & infovalue', 'userid', 'resolver', 'assigned'];
  challengesApiFilter = ['serial', 'transaction_id'];
  challengesAdvancedApiFilter = [];
  private tokenBaseUrl = environment.proxyUrl + '/token/';
  private stopPolling$ = new Subject<void>();

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
    private notificationService: NotificationService,
  ) {}

  toggleActive(tokenSerial: string, active: boolean): Observable<any> {
    const headers = this.localService.getHeaders();
    const action = active ? 'disable' : 'enable';
    return this.http
      .post(
        `${this.tokenBaseUrl}${action}`,
        { serial: tokenSerial },
        { headers },
      )
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

  resetFailCount(tokenSerial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http
      .post(this.tokenBaseUrl + 'reset', { serial: tokenSerial }, { headers })
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

  getTokenData(
    page: number,
    pageSize: number,
    sort?: Sort,
    filterValue?: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams()
      .set('page', page.toString())
      .set('pagesize', pageSize.toString());

    if (sort) {
      params = params.set('sortby', sort.active).set('sortdir', sort.direction);
    }

    if (filterValue) {
      const combinedFilters = [...this.apiFilter, ...this.advancedApiFilter];
      const { filterPairs, remainingFilterText } =
        this.tableUtilsService.parseFilterString(filterValue, combinedFilters);
      filterPairs.forEach(({ key, value }) => {
        if (
          key === 'user' ||
          key === 'infokey' ||
          key === 'infovalue' ||
          key === 'active' ||
          key === 'assigned' ||
          key === 'container_serial'
        ) {
          params = params.set(key, `${value}`);
        } else {
          params = params.set(key, `*${value}*`);
        }
      });

      /* TODO global filtering is missing in api
      if (remainingFilterText) {
        params = params.set('globalfilter', `*${remainingFilterText}*`);
      }
      */
    }

    return this.http.get<any>(this.tokenBaseUrl, { headers, params }).pipe(
      catchError((error) => {
        console.error('Failed to get token data.', error);
        const message = error.error?.result?.error?.message || '';
        this.notificationService.openSnackBar(
          'Failed to get token data. ' + message,
        );
        return throwError(() => error);
      }),
    );
  }

  getTokenDetails(tokenSerial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams().set('serial', tokenSerial);
    return this.http.get(this.tokenBaseUrl, { headers, params });
  }

  setTokenDetail(
    tokenSerial: string,
    key: string,
    value: any,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;

    const payload =
      key === 'maxfail'
        ? { serial: tokenSerial, max_failcount: value }
        : { serial: tokenSerial, [key]: value };

    return this.http.post(set_url, payload, { headers }).pipe(
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

  setTokenInfos(tokenSerial: string, infos: any): Observable<any> {
    const headers = this.localService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;
    const info_url = `${this.tokenBaseUrl}info`;

    const postRequest = (url: string, body: any) => {
      return this.http.post(url, body, { headers }).pipe(
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

  unassignUser(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}unassign`,
        { serial: tokenSerial },
        { headers },
      )
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

  assignUser(
    tokenSerial: string,
    username: string,
    realm: string,
    pin: string,
  ) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.tokenBaseUrl}assign`,
        {
          serial: tokenSerial,
          user: username,
          realm: realm,
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
      .post(
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

  setTokengroup(tokenSerial: string, value: any) {
    const headers = this.localService.getHeaders();
    const valueArray = Array.isArray(value) ? value : Object.values(value);
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

  getTokengroups() {
    const headers = this.localService.getHeaders();
    return this.http
      .get(environment.proxyUrl + `/tokengroup/`, { headers })
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

  lostToken(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post(`${this.tokenBaseUrl}lost/` + tokenSerial, {}, { headers })
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

  getSerial(otp: string, params: HttpParams): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http
      .get(`${this.tokenBaseUrl}getserial/${otp}`, {
        params: params,
        headers: headers,
      })
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

  enrollToken(options: any): Observable<any> {
    const headers = this.localService.getHeaders();

    const payload: any = {
      type: options.type,
      description: options.description,
      container_serial: options.container_serial,
      validity_period_start: options.validity_period_start,
      validity_period_end: options.validity_period_end,
      pin: options.pin,
    };

    if (!options.onlyAddToRealm) {
      payload.user = options.user;
    }

    if (options.type === 'passkey') {
      Object.entries(options).forEach(([key, value]) => {
        payload[key] = value;
      });
    }

    if (['hotp', 'totp', 'motp', 'applspec'].includes(options.type)) {
      payload.otpkey = options.generateOnServer ? null : options.otpKey;
      payload.genkey = options.generateOnServer ? 1 : 0;
    }

    if (options.type === 'push') {
      payload.genkey = 1;
    }

    if (['daypassword', 'indexedsecret'].includes(options.type)) {
      payload.otpkey = options.otpKey;
    }

    if (['hotp', 'totp', 'daypassword'].includes(options.type)) {
      payload.otplen = Number(options.otpLength);
      payload.hashlib = options.hashAlgorithm;
    }

    if (['totp', 'daypassword'].includes(options.type)) {
      payload.timeStep = options.timeStep;
    }

    if (options.type === 'motp') {
      payload.motppin = options.motpPin;
    }

    if (options.type === 'sshkey') {
      payload.sshkey = options.sshPublicKey;
    }

    if (options.type === 'yubikey') {
      payload.otplen = Number(options.otpLength);
      payload.otpkey = options.otpKey;
    }

    if (options.type === 'yubico') {
      payload['yubico.tokenid'] = options.yubicoIdentifier;
    }

    if (options.type === 'radius') {
      payload['radius.identifier'] = options.radiusServerConfiguration;
      payload['radius.user'] = options.radiusUser;
    }

    if (options.type === 'remote') {
      payload['remote.server_id'] = options.remoteServer;
      payload['remote.serial'] = options.remoteSerial;
      payload['remote.user'] = options.remoteUser;
      payload['remote.realm'] = options.remoteRealm;
      payload['remote.resolver'] = options.remoteResolver;
      payload['remote.local_checkpin'] = options.checkPinLocally;
    }

    if (options.type === 'sms') {
      payload['sms.identifier'] = options.smsGateway;
      payload['phone'] = options.readNumberDynamically
        ? null
        : options.phoneNumber;
      payload['dynamic_phone'] = options.readNumberDynamically;
    }

    if (options.type === '4eyes') {
      payload.separator = options.separator;
      payload['4eyes'] = options.requiredTokenOfRealms?.reduce(
        (acc: any, curr: any) => {
          acc[curr.realm] = {
            count: curr.tokens,
            selected: true,
          };
          return acc;
        },
        {} as Record<string, { count: number; selected: boolean }>,
      );

      if (options.onlyAddToRealm) {
        payload.realm = options.userRealm;
      }
    }

    if (options.type === 'applspec') {
      payload.service_id = options.serviceId;
    }

    if (options.type === 'certificate') {
      payload.genkey = 1;
      payload.ca = options.caConnector;
      payload.template = options.certTemplate;
      payload.pem = options.pem;
    }

    if (options.type === 'email') {
      payload.email = options.emailAddress;
      payload.dynamic_email = options.readEmailDynamically;
    }

    if (options.type === 'question') {
      payload.questions = options.answers;
    }

    if (options.type === 'vasco') {
      if (options.useVascoSerial) {
        payload.serial = options.vascoSerial;
      }
      payload.otpkey = options.otpKey;
      payload.genkey = 0;
    }

    return this.http
      .post(`${this.tokenBaseUrl}init`, payload, { headers })
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

  pollTokenState(tokenSerial: string, startTime: number): Observable<any> {
    return timer(startTime, 2000).pipe(
      takeUntil(this.stopPolling$),
      switchMap(() => this.getTokenDetails(tokenSerial)),
      takeWhile(
        (response: any) =>
          response.result.value.tokens[0].rollout_state === 'clientwait',
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
    );
  }

  stopPolling() {
    this.stopPolling$.next();
  }

  getChallenges(named: {
    pageIndex: number;
    pageSize: number;
    sort: Sort;
    filterValue: string;
  }): Observable<any> {
    const { pageIndex, pageSize, sort, filterValue } = named;
    const headers = this.localService.getHeaders();
    let params = new HttpParams()
      .set('page', pageIndex.toString())
      .set('pagesize', pageSize.toString());

    if (sort) {
      params = params.set('sortby', sort.active).set('sortdir', sort.direction);
    }

    const combinedFilters = [
      ...this.challengesApiFilter,
      ...this.challengesAdvancedApiFilter,
    ];
    let urlPath = 'challenges/';
    if (filterValue) {
      const { filterPairs, remainingFilterText } =
        this.tableUtilsService.parseFilterString(filterValue, combinedFilters);
      filterPairs.forEach(({ key, value }) => {
        if (key === 'serial') {
          urlPath = `challenges/*${value}*`;
        } else {
          params = params.set(key, `*${value}*`);
        }
      });
      /* global filtering is missing in api
        if (remainingFilterText) {
          params = params.set('globalfilter', `*${remainingFilterText}*`);
        } */
    }

    return this.http
      .get<any>(this.tokenBaseUrl + urlPath, {
        headers,
        params,
      })
      .pipe(
        catchError((error) => {
          console.error('Failed to load challenges.', error);
          return throwError(() => error);
        }),
      );
  }
}
