import {Injectable} from '@angular/core';
import {HttpClient, HttpHeaders, HttpParams} from '@angular/common/http';
import {Observable, throwError} from 'rxjs';
import {catchError, map} from 'rxjs/operators';
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

  toggleActive(element: any): Observable<any> {
    const headers = this.getHeaders();
    const action = element.active ? 'disable' : 'enable';
    return this.http.post(`${this.baseUrl}${action}`, {"serial": element.serial}, {headers}).pipe(
      catchError(error => {
        console.error(`Failed to ${action} token`, error);
        return throwError(error);
      })
    );
  }

  resetFailCount(element: any): Observable<any> {
    const headers = this.getHeaders();
    return this.http.post(this.baseUrl + 'reset', {"serial": element.serial}, {headers}).pipe(
      catchError(error => {
        console.error('Failed to get reset fail counter', error);
        return throwError(error);
      })
    )
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

    return this.http.get<any>(this.baseUrl, {headers, params}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to get token data', error);
        return throwError(error);
      })
    );
  }

  getTokenDetails(serial: string): Observable<any> {
    const headers = this.getHeaders();
    let params = new HttpParams().set('serial', serial);
    return this.http.get(this.baseUrl, {headers, params}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to get token details', error);
        return throwError(error);
      })
    );
  }
}
