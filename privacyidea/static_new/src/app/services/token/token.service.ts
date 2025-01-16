import {Injectable} from '@angular/core';
import {HttpClient, HttpParams} from '@angular/common/http';
import {forkJoin, Observable} from 'rxjs';
import {LocalService} from '../local/local.service';
import {Sort} from '@angular/material/sort';
import {TableUtilsService} from '../table-utils/table-utils.service';

@Injectable({
  providedIn: 'root'
})
export class TokenService {
  private tokenBaseUrl = '/token/';
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

  advancedApiFilter = [
    'infokey & infovalue',
    'userid',
    'resolver',
    'assigned',
  ]

  constructor(private http: HttpClient,
              private localService: LocalService,
              private tableUtilsService: TableUtilsService) {
  }

  toggleActive(serial: string, active: boolean): Observable<any> {
    const headers = this.localService.getHeaders();
    const action = active ? 'disable' : 'enable';
    return this.http.post(`${this.tokenBaseUrl}${action}`, {"serial": serial}, {headers})
  }

  resetFailCount(serial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.post(this.tokenBaseUrl + 'reset', {"serial": serial}, {headers})
  }

  getTokenData(page: number, pageSize: number, sort?: Sort, filterValue?: string): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams()
      .set('page', page.toString())
      .set('pagesize', pageSize.toString());

    if (sort) {
      params = params
        .set('sortby', sort.active)
        .set('sortdir', sort.direction);
    }

    if (filterValue) {
      const combinedFilters = [...this.apiFilter, ...this.advancedApiFilter];
      const {
        filterPairs,
        remainingFilterText
      } = this.tableUtilsService.parseFilterString(filterValue, combinedFilters);
      filterPairs.forEach(({label, value}) => {
        if (label === 'user' || label === 'infokey' || label === 'infovalue' || label === 'active'
          || label === 'assigned' || label === 'container_serial') {
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

    return this.http.get<any>(this.tokenBaseUrl, {headers, params})
  }

  getTokenDetails(serial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams().set('serial', serial);
    return this.http.get(this.tokenBaseUrl, {headers, params})
  }

  setTokenDetail(serial: string, key: string, value: any): Observable<any> {
    const headers = this.localService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;
    if (key === 'maxfail') {
      return this.http.post(set_url, {serial, ["max_failcount"]: value}, {headers});
    } else {
      return this.http.post(set_url, {serial, [key]: value}, {headers});
    }
  }

  setTokenInfos(serial: string, infos: any): Observable<any> {
    const headers = this.localService.getHeaders();
    const set_url = `${this.tokenBaseUrl}set`;
    const info_url = `${this.tokenBaseUrl}info`;
    const requests = Object.keys(infos).map(info => {
        const infoKey = info;
        const infoValue = infos[infoKey];
        if (infoKey === "count_auth_max" || infoKey === "count_auth_success_max" || infoKey === "hashlib"
          || infoKey === "validity_period_start" || infoKey === "validity_period_end") {
          return this.http.post(set_url, {serial, [infoKey]: infoValue}, {headers})
        } else {
          return this.http.post(`${info_url}/${serial}/${infoKey}`, {["value"]: infoValue}, {headers})
        }
      }
    );
    return forkJoin(requests);
  }


  deleteToken(serial: string) {
    const headers = this.localService.getHeaders();
    return this.http.delete(this.tokenBaseUrl + serial, {headers})
  }

  revokeToken(serial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}revoke`, {'serial': serial}, {headers})
  }

  deleteInfo(serial: string, infoKey: string) {
    const headers = this.localService.getHeaders();
    return this.http.delete(`${this.tokenBaseUrl}info/` + serial + "/" + infoKey, {headers})
  }

  unassignUser(serial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}unassign`, {serial}, {headers})
  }

  assignUser(serial: string, username: string | null, realm: string, pin: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}assign`, {
      serial: serial,
      user: username,
      realm: realm,
      pin: pin,
    }, {headers})
  }

  setPin(serial: string, userPin: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}setpin`, {
      serial: serial,
      otppin: userPin
    }, {headers})
  }

  setRandomPin(serial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}setrandompin`, {
      serial: serial
    }, {headers})
  }

  resyncOTPToken(serial: string, fristOTPValue: string, secondOTPValue: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}resync`, {
      serial: serial,
      otp1: fristOTPValue,
      otp2: secondOTPValue
    }, {headers})
  }

  setTokenRealm(serial: string, value: string[] | null) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}realm/` + serial, {
      realms: value
    }, {headers})
  }

  setTokengroup(serial: string, value: any) {
    const headers = this.localService.getHeaders();
    const valueArray = Array.isArray(value) ? value : Object.values(value);
    return this.http.post(`${this.tokenBaseUrl}group/` + serial, {
      groups: valueArray
    }, {headers});
  }

  getTokengroups() {
    const headers = this.localService.getHeaders();
    return this.http.get(`/tokengroup`, {headers})
  }

  lostToken(serial: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.tokenBaseUrl}lost/` + serial, {headers});
  }
}
