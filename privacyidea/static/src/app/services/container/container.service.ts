import {Injectable} from '@angular/core';
import {HttpClient, HttpParams} from '@angular/common/http';
import {Observable, throwError} from 'rxjs';
import {catchError, map} from 'rxjs/operators';
import {LocalService} from '../local/local.service';
import {Sort} from '@angular/material/sort';
import {TableUtilsService} from '../table-utils/table-utils.service';

@Injectable({
  providedIn: 'root'
})
export class ContainerService {
  private containerBaseUrl = 'http://127.0.0.1:5000/container/';
  apiFilter = [
    'container_serial',
    'type',
    'user',
  ];
  advancedApiFilter = [
    'token_serial'
  ];

  constructor(private http: HttpClient,
              private localService: LocalService,
              private tableUtilsService: TableUtilsService) {
  }

  getContainerData(page?: number, pageSize?: number, sort?: Sort, filterValue?: string): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams()

    if (page && pageSize) {
      params = params
        .set('page', page.toString())
        .set('pagesize', pageSize.toString());
    }
    if (sort) {
      params = params
        .set('sortby', sort.active)
        .set('sortdir', sort.direction);
    }

    if (filterValue) {
      const {
        filterPairs,
        remainingFilterText
      } = this.tableUtilsService.parseFilterString(filterValue, this.apiFilter);

      filterPairs.forEach(({label, value}) => {
        if (label === 'user' || label === 'generic' || label === 'container_serial' || label === 'token_serial') {
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

    return this.http.get<any>(this.containerBaseUrl, {headers, params}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to get container data', error);
        return throwError(error);
      })
    );
  }

  assignContainer(token_serial: string, container_serial: string | null) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.containerBaseUrl}${container_serial}/add`, {
      serial: token_serial
    }, {headers}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to assign container', error);
        return throwError(error);
      })
    );
  }

  unassignContainer(token_serial: string, container_serial: string | null) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.containerBaseUrl}${container_serial}/remove`, {
      serial: token_serial
    }, {headers}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to unassign container', error);
        return throwError(error);
      })
    )
  }

  getContainerDetails(serial: string): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams().set('container_serial', serial);
    return this.http.get(this.containerBaseUrl, {headers, params})
  }

  setContainerRealm(serial: string, value: string[] | null) {
    const headers = this.localService.getHeaders();
    let valueString = value ? value.join(',') : '';
    return this.http.post(`${this.containerBaseUrl}${serial}/realms`, {
      realms: valueString
    }, {headers})
  }

  setContainerDescription(serial: string, value: any) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.containerBaseUrl}${serial}/description`, {
      description: value
    }, {headers})
  }

  toggleActive(serial: string, states: string[]): Observable<any> {
    const headers = this.localService.getHeaders();
    const new_states = states.map(state => {
      if (state === 'active') {
        return 'disabled'
      } else if (state === 'disabled') {
        return 'active'
      } else {
        return state
      }
    }).join(',');
    return this.http.post(`${this.containerBaseUrl}${serial}/states`, {states: new_states}, {headers})
  }

  unassignUser(serial: string, username: string, userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.containerBaseUrl}${serial}/unassign`, {
      user: username,
      realm: userRealm
    }, {headers})
  }

  assignUser(serial: string, username: string, userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http.post(`${this.containerBaseUrl}${serial}/assign`, {
      user: username,
      realm: userRealm
    }, {headers})
  }

  setContainerInfos(serial: string, infos: any) {
    const headers = this.localService.getHeaders();
    const info_url = `${this.containerBaseUrl}${serial}/info`;
    return Object.keys(infos).map(info => {
        const infoKey = info;
        const infoValue = infos[infoKey];
        return this.http.post(`${info_url}/${infoKey}`, {value: infoValue}, {headers})
      }
    );
  }

  deleteInfo(serial: string, key: string) {
    const headers = this.localService.getHeaders();
    //TODO: API is missing the delete endpoint
    return;
  }
}
