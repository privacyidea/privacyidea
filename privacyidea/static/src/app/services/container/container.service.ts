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
export class ContainerService {
  private baseUrl = 'http://127.0.0.1:5000/container/';
  apiFilter = [
    'user',
    'container_serial',
    'type',
    'token_serial', /*TODO fix not working and missing query params*/
  ];

  constructor(private http: HttpClient,
              private localStore: LocalService,
              private tableUtilsService: TableUtilsService) {
  }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'PI-Authorization': this.localStore.getData('bearer_token') || ''
    });
  }

  getContainerData(page?: number, pageSize?: number, sort?: Sort, filterValue?: string): Observable<any> {
    const headers = this.getHeaders();
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
      const {filterPairs, remainingFilterText} = this.tableUtilsService.parseFilterString(filterValue, this.apiFilter);

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

    return this.http.get<any>(this.baseUrl, {headers, params}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to get container data', error);
        return throwError(error);
      })
    );
  }

  assignContainer(token_serial: string, container_serial: string) {
    const headers = this.getHeaders();
    return this.http.post(`${this.baseUrl}${container_serial}/add`, {
      serial: token_serial
    }, {headers}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to assign container', error);
        return throwError(error);
      })
    );
  }

  unassignContainer(token_serial: string, container_serial: string) {
    const headers = this.getHeaders();
    return this.http.post(`${this.baseUrl}${container_serial}/remove`, {
      serial: token_serial
    }, {headers}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to unassign container', error);
        return throwError(error);
      })
    );
  }
}
