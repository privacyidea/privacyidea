import {Injectable} from '@angular/core';
import {HttpClient, HttpHeaders, HttpParams} from '@angular/common/http';
import {Observable, throwError} from 'rxjs';
import {catchError, map} from 'rxjs/operators';
import {LocalService} from '../local/local.service';
import {Sort} from '@angular/material/sort';

@Injectable({
  providedIn: 'root'
})
export class TokenService {
  private baseUrl = 'http://127.0.0.1:5000/token/';

  private apiColumnMap = {
    description: 'description',
    resolver: 'resolver',
    rollout_state: 'rollout_state',
    serial: 'serial',
    realms: 'tokenrealm',
    tokentype: 'type',
    username: 'userid' // TODO username is not userid
  };

  constructor(private http: HttpClient, private localStore: LocalService) {
  }

  getTokenData(page: number, pageSize: number, columns: {
    key: string;
    label: string
  }[], sort?: Sort, filterValue?: string): Observable<any> {
    const headers = new HttpHeaders({
      'PI-Authorization': this.localStore.getData('bearer_token') || ''
    });

    let params = new HttpParams()
      .set('page', page.toString())
      .set('pagesize', pageSize.toString());

    const appliedKeys = new Set<string>();

    if (sort) {
      params = params
        .set('sortby', sort.active)
        .set('sortdir', sort.direction);
    }

    if (filterValue) {
      const lowerFilterValue = filterValue.trim().toLowerCase();
      const filterLabels = columns.map(column => column.label.toLowerCase() + ':');

      const filterValueSplit = lowerFilterValue.split(' ');
      const filterPairs = [] as { label: string; value: string }[];

      let currentLabel = '';
      let currentValue = '';
      let remainingFilterText = '';

      const findMatchingLabel = (filterValueSplit: string[]): string | null => {
        for (let i = 1; i <= filterValueSplit.length; i++) {
          const possibleLabel = filterValueSplit.slice(0, i).join(' ');
          if (filterLabels.includes(possibleLabel)) {
            return possibleLabel;
          }
        }
        return null;
      };

      let i = 0;
      while (i < filterValueSplit.length) {
        const remainingFilterValues = filterValueSplit.slice(i);
        const matchingLabel = findMatchingLabel(remainingFilterValues);

        if (matchingLabel) {
          if (currentLabel && currentValue) {
            filterPairs.push({label: currentLabel.slice(0, -1), value: currentValue.trim()});
          }
          currentLabel = matchingLabel;
          currentValue = '';
          i += matchingLabel.split(' ').length;
        } else if (currentLabel) {
          currentValue += filterValueSplit[i] + ' ';
          i++;
        } else {
          remainingFilterText += filterValueSplit[i] + ' ';
          i++;
        }
      }
      if (currentLabel && currentValue) {
        filterPairs.push({label: currentLabel.slice(0, -1), value: currentValue.trim()});
      }
      filterPairs.forEach(({label, value}) => {
        const column = columns.find(col => col.label.toLowerCase() === label);
        if (column) {
          const apiColumnKey = this.apiColumnMap[column.key as keyof typeof this.apiColumnMap];
          if (apiColumnKey) {
            params = params.set(apiColumnKey, `*${value}*`);
            appliedKeys.add(apiColumnKey);
          }
        }
      });

      /*remainingFilterText = remainingFilterText.trim();
      if (remainingFilterText) {
        params = params.set('globalfilter', `*${remainingFilterText}*`);
      }*/
    }

    Object.keys(this.apiColumnMap).forEach((frontendKey) => {
      const key = frontendKey as keyof typeof this.apiColumnMap;
      const apiKey = this.apiColumnMap[key];
      if (!appliedKeys.has(apiKey)) {
        params = params.set(apiKey, '**');
      }
    });

    return this.http.get<any>(this.baseUrl, {headers, params}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to get token data', error);
        return throwError(error);
      })
    );
  }
}
