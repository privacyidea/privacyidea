import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { LocalService } from '../local/local.service';
import { Sort } from '@angular/material/sort';
import { TableUtilsService } from '../table-utils/table-utils.service';
import { TokenType } from '../../components/token/token.component';

export interface EnrollmentOptions {
  type: TokenType;
  description: string;
  tokenSerial: string;
  user: string;
  container_serial: string;
  validity_period_start: string;
  validity_period_end: string;
  pin: string;
  generateOnServer?: boolean;
  otpLength?: number;
  otpKey?: string;
  hashAlgorithm?: string;
  timeStep?: number;
  motpPin?: string;
  remoteServer?: { url: string; id: string };
  remoteSerial?: string;
  remoteUser?: string;
  remoteRealm?: string;
  remoteResolver?: string;
  checkPinLocally?: boolean;
  sshPublicKey?: string;
  yubicoIdentifier?: string;
  radiusServerConfiguration?: string;
  radiusUser?: string;
  smsGateway?: string;
  phoneNumber?: string;
  readNumberDynamically?: boolean;
  separator?: string;
  requiredTokenOfRealms?: { realm: string; tokens: number }[];
  serviceId?: string;
  caConnector?: string;
  certTemplate?: string;
  pem?: string;
  emailAddress?: string;
  readEmailDynamically?: boolean;
}

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
  private tokenBaseUrl = '/token/';

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
  ) {}

  toggleActive(tokenSerial: string, active: boolean): Observable<any> {
    const headers = this.localService.getHeaders();
    const action = active ? 'disable' : 'enable';
    return this.http.post(
      `${this.tokenBaseUrl}${action}`,
      { serial: tokenSerial },
      { headers },
    );
  }

  resetFailCount(tokenSerial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.post(
      this.tokenBaseUrl + 'reset',
      { serial: tokenSerial },
      { headers },
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
      filterPairs.forEach(({ label, value }) => {
        if (
          label === 'user' ||
          label === 'infokey' ||
          label === 'infovalue' ||
          label === 'active' ||
          label === 'assigned' ||
          label === 'container_serial'
        ) {
          params = params.set(label, `${value}`);
        } else {
          params = params.set(label, `*${value}*`);
        }
      });

      /* TODO global filtering is missing in api
      if (remainingFilterText) {
        params = params.set('globalfilter', `*${remainingFilterText}*`);
      }
      */
    }

    return this.http.get<any>(this.tokenBaseUrl, { headers, params });
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
    if (key === 'maxfail') {
      return this.http.post(
        set_url,
        { serial: tokenSerial, ['max_failcount']: value },
        { headers },
      );
    } else {
      return this.http.post(
        set_url,
        { serial: tokenSerial, [key]: value },
        { headers },
      );
    }
  }

  setTokenInfos(tokenSerial: string, infos: any): Observable<any> {
    const headers = this.localService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;
    const info_url = `${this.tokenBaseUrl}info`;
    const requests = Object.keys(infos).map((info) => {
      const infoKey = info;
      const infoValue = infos[infoKey];
      if (
        infoKey === 'count_auth_max' ||
        infoKey === 'count_auth_success_max' ||
        infoKey === 'hashlib' ||
        infoKey === 'validity_period_start' ||
        infoKey === 'validity_period_end'
      ) {
        return this.http.post(
          set_url,
          { serial: tokenSerial, [infoKey]: infoValue },
          { headers },
        );
      } else {
        return this.http.post(
          `${info_url}/${tokenSerial}/${infoKey}`,
          { ['value']: infoValue },
          { headers },
        );
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
    return this.http.post(
      `${this.tokenBaseUrl}revoke`,
      { serial: tokenSerial },
      { headers },
    );
  }

  deleteInfo(tokenSerial: string, infoKey: string) {
    const headers = this.localService.getHeaders();
    return this.http.delete(
      `${this.tokenBaseUrl}info/` + tokenSerial + '/' + infoKey,
      { headers },
    );
  }

  unassignUser(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.tokenBaseUrl}unassign`,
      { serial: tokenSerial },
      { headers },
    );
  }

  assignUser(
    tokenSerial: string,
    username: string,
    realm: string,
    pin: string,
  ) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.tokenBaseUrl}assign`,
      {
        serial: tokenSerial,
        user: username,
        realm: realm,
        pin: pin,
      },
      { headers },
    );
  }

  setPin(tokenSerial: string, userPin: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.tokenBaseUrl}setpin`,
      {
        serial: tokenSerial,
        otppin: userPin,
      },
      { headers },
    );
  }

  setRandomPin(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.tokenBaseUrl}setrandompin`,
      {
        serial: tokenSerial,
      },
      { headers },
    );
  }

  resyncOTPToken(
    tokenSerial: string,
    fristOTPValue: string,
    secondOTPValue: string,
  ) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.tokenBaseUrl}resync`,
      {
        serial: tokenSerial,
        otp1: fristOTPValue,
        otp2: secondOTPValue,
      },
      { headers },
    );
  }

  setTokenRealm(tokenSerial: string, value: string[]) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.tokenBaseUrl}realm/` + tokenSerial,
      {
        realms: value,
      },
      { headers },
    );
  }

  setTokengroup(tokenSerial: string, value: any) {
    const headers = this.localService.getHeaders();
    const valueArray = Array.isArray(value) ? value : Object.values(value);
    return this.http.post(
      `${this.tokenBaseUrl}group/` + tokenSerial,
      {
        groups: valueArray,
      },
      { headers },
    );
  }

  getTokengroups() {
    const headers = this.localService.getHeaders();
    return this.http.get(`/tokengroup`, { headers });
  }

  lostToken(tokenSerial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.tokenBaseUrl}lost/` + tokenSerial,
      {},
      { headers },
    );
  }

  getSerial(otp: string, params: HttpParams): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.get(`${this.tokenBaseUrl}getserial/${otp}`, {
      params: params,
      headers: headers,
    });
  }

  enrollToken(options: EnrollmentOptions) {
    const headers = this.localService.getHeaders();

    const payload: any = {
      type: options.type,
      description: options.description,
      user: options.user,
      container_serial: options.container_serial,
      validity_period_start: options.validity_period_start,
      validity_period_end: options.validity_period_end,
      pin: options.pin,
    };

    if (['hotp', 'totp', 'motp', 'applspec'].includes(options.type)) {
      payload.otpkey = options.generateOnServer ? null : options.otpKey;
      payload.genkey = options.generateOnServer ? 1 : 0;
    }

    if (['daypassword', 'indexedsecret'].includes(options.type)) {
      payload.otpkey = options.otpKey;
    }

    if (['hotp', 'totp', 'daypassword'].includes(options.type)) {
      payload.otplen = Number(options.otpLength);
      payload.hashlib = options.hashAlgorithm;
    }

    if (['totp', 'daypassword'].includes(options.type)) {
      payload.timeStep = Number(options.timeStep);
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
        (acc, curr) => {
          acc[curr.realm] = {
            count: curr.tokens,
            selected: true,
          };
          return acc;
        },
        {} as Record<string, { count: number; selected: boolean }>,
      );
    }

    if (options.type === 'applspec') {
      payload.service_id = options.serviceId;
    }

    if (options.type === 'certificate') {
      payload.ca = options.caConnector;
      payload.template = options.certTemplate;
      payload.pem = options.pem;
    }

    if (options.type === 'email') {
      payload.email = options.emailAddress;
      payload.dynamic_email = options.readEmailDynamically;
    }

    return this.http.post(`${this.tokenBaseUrl}init`, payload, { headers });
  }
}
