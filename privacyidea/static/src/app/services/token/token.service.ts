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
  apiFilter = [
    'serial',
    'type',
    'tokenrealm',
    'description',
    'rollout_state',
    'userid',
    'resolver',
    /*'user',
    'assigned',
    'active',
    'infokey',
    'infovalue',
    'container_serial', TODO fix not working query params*/
  ];

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
      const filterLabels = this.apiFilter.map(column => column.toLowerCase() + ':');

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
          params = params.set(label, `*${value}*`);
          appliedKeys.add(label);
        }
      );

      /*remainingFilterText = remainingFilterText.trim();
      if (remainingFilterText) {
        params = params.set('globalfilter', `*${remainingFilterText}*`);
      }*/
    }

    return this.http.get<any>(this.baseUrl, {headers, params}).pipe(
      map(response => response),
      catchError(error => {
        console.error('Failed to get token data', error);
        return throwError(error);
      })
    );
  }
}
