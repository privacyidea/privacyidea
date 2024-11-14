import {Injectable} from '@angular/core';
import {HttpClient, HttpHeaders, HttpParams} from '@angular/common/http';
import {forkJoin, Observable} from 'rxjs';
import {LocalService} from '../local/local.service';
import {Sort} from '@angular/material/sort';
import {TableUtilsService} from '../table-utils/table-utils.service';

@Injectable({
  providedIn: 'root'
})
export class TokenService {
  private baseUrl = 'http://127.0.0.1:5000/token/';
  apiFilter = [
    'serial',
    'type',
    'tokenrealm',
    'description',
    'user',
    'rollout_state',
    'userid',
    'resolver',
    'active',
    'assigned',
    'infokey',
    'infovalue',
    'container_serial',
  ];

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'PI-Authorization': this.localStore.getData('bearer_token') || ''
    });
  }

  constructor(private http: HttpClient,
              private localStore: LocalService,
              private tableUtilsService: TableUtilsService) {
  }

  toggleActive(serial: string, active: boolean): Observable<any> {
    const headers = this.getHeaders();
    const action = active ? 'disable' : 'enable';
    return this.http.post(`${this.baseUrl}${action}`, {"serial": serial}, {headers})
  }

  resetFailCount(serial: string): Observable<any> {
    const headers = this.getHeaders();
    return this.http.post(this.baseUrl + 'reset', {"serial": serial}, {headers})
  }

  getTokenData(page: number, pageSize: number, columns: {
    key: string;
    label: string
  }[], sort?: Sort, filterValue?: string): Observable<any> {
    const headers = this.getHeaders();
    let params = new HttpParams()
      .set('page', page.toString())
      .set('pagesize', pageSize.toString());

    if (sort) {
      params = params
        .set('sortby', sort.active)
        .set('sortdir', sort.direction);
    }

    if (filterValue) {
      const {filterPairs, remainingFilterText} = this.tableUtilsService.parseFilterString(filterValue, this.apiFilter);

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

    return this.http.get<any>(this.baseUrl, {headers, params})
  }

  getTokenDetails(serial: string): Observable<any> {
    const headers = this.getHeaders();
    let params = new HttpParams().set('serial', serial);
    return this.http.get(this.baseUrl, {headers, params})
  }

  setTokenDetail(serial: string, key: string, value: any, infos_signal: any): Observable<any> {
    const headers = this.getHeaders();
    const set_url = `${this.baseUrl}set`;
    const info_url = `${this.baseUrl}info`;
    if (key === 'info' && typeof infos_signal === 'object' && infos_signal !== null) {
      const requests = Object.keys(infos_signal).map(index => {
          const infoKey = infos_signal[index].split(':')[0];
          const infoValue = infos_signal[index].split(' ')[1];
          if (infoKey === "count_auth_max" || infoKey === "count_auth_success_max" || infoKey === "hashlib"
            || infoKey === "validity_period_start" || infoKey === "validity_period_end") {
            return this.http.post(set_url, {serial, [infoKey]: infoValue}, {headers})
          } else {
            return this.http.post(`${info_url}/${serial}/${infoKey}`, {["value"]: infoValue}, {headers})
          }
        }
      );
      return forkJoin(requests);
    } else {
      if (key === 'maxfail') {
        return this.http.post(set_url, {serial, ["max_failcount"]: value}, {headers});
      } else {
        return this.http.post(set_url, {serial, [key]: value}, {headers});
      }
    }
  }

  deleteToken(serial: string) {
    const headers = this.getHeaders();
    return this.http.delete(this.baseUrl + serial, {headers})
  }

  revokeToken(serial: string) {
    const headers = this.getHeaders();
    return this.http.post(`${this.baseUrl}revoke`, {'serial': serial}, {headers})
  }

  deleteInfo(serial: string, infoKey: string) {
    const headers = this.getHeaders();
    return this.http.delete(`${this.baseUrl}info` + "/" + serial + "/" + infoKey, {headers})
  }

  unassignUser(serial: string) {
    const headers = this.getHeaders();
    return this.http.post(`${this.baseUrl}unassign`, {serial}, {headers})
  }

  assignUser(serial: string, username: string, realm: string, pin: string) {
    const headers = this.getHeaders();
    return this.http.post(`${this.baseUrl}assign`, {
      serial: serial,
      user: username,
      realm: realm,
      pin: pin,
    }, {headers})
  }

  getRealms(): Observable<any> {
    const headers = this.getHeaders();
    return this.http.get('http://127.0.0.1:5000/realm', {headers})
  }
}
