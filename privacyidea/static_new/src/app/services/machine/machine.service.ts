import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs/internal/Observable';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { TableUtilsService } from '../table-utils/table-utils.service';

@Injectable({
  providedIn: 'root',
})
export class MachineService {
  baseUrl: string = environment.proxyUrl + '/machine/';
  sshApiFilter = ['serial', 'service_id'];
  sshAdvancedApiFilter = ['hostname', 'machineid & resolver'];
  offlineApiFilter = ['serial'];
  offlineAdvancedApiFilter = [
    'hostname',
    'machineid & resolver',
    'count',
    'rounds',
  ];

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
  ) {}

  postTokenOption(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
    mtid: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.baseUrl}tokenoption`,
      { hostname, machineid, resolver, serial, application, mtid },
      { headers },
    );
  }

  getAuthItem(
    challenge: string,
    hostname: string,
    application?: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams()
      .set('challenge', challenge)
      .set('hostname', hostname);
    return this.http.get(
      application
        ? `${this.baseUrl}authitem/${application}`
        : `${this.baseUrl}authitem`,
      {
        headers,
        params,
      },
    );
  }

  postToken(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.baseUrl}token`,
      { hostname, machineid, resolver, serial, application },
      { headers },
    );
  }

  getTokenMachineData(
    pageSize: number,
    currentFilter: string,
    application: 'ssh' | 'offline',
    sortby?: string,
    sortdir?: string,
    page?: number,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams().set('application', application);

    if (page) {
      params = params.set('page', page.toString());
    }
    params = params.set('pagesize', pageSize.toString());
    if (sortby) {
      params = params.set('sortby', sortby);
    }
    if (sortdir) {
      params = params.set('sortdir', sortdir);
    }

    if (currentFilter) {
      const combinedFilters = [
        ...this.sshApiFilter,
        ...this.sshAdvancedApiFilter,
      ];
      const { filterPairs, remainingFilterText } =
        this.tableUtilsService.parseFilterString(
          currentFilter,
          combinedFilters,
        );
      filterPairs.forEach(({ key, value }) => {
        if (['serial'].includes(key)) {
          params = params.set(key, `*${value}*`);
        }
        if (['hostname', 'machineid', 'resolver'].includes(key)) {
          params = params.set(key, `${value}`);
        }
        switch (application) {
          case 'ssh':
            if (['service_id'].includes(key)) {
              params = params.set(key, `*${value}*`);
            }
            break;
          case 'offline':
            if (['count', 'rounds'].includes(key)) {
              params = params.set(key, value);
            }
            break;
        }
      });
      // if (remainingFilterText) {
      //   params = params.set('globalfilter', `*${remainingFilterText}*`);
      // }
    }

    return this.http.get(`${this.baseUrl}token`, { headers, params });
  }

  getMachine(
    hostname: string,
    ip: string,
    id: string,
    resolver: string,
    any: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams()
      .set('hostname', hostname)
      .set('ip', ip)
      .set('id', id)
      .set('resolver', resolver)
      .set('any', any);
    return this.http.get(`${this.baseUrl}`, { headers, params });
  }

  deleteToken(
    serial: string,
    machineid: string,
    resolver: string,
    application: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.delete(
      `${this.baseUrl}token/${serial}/${machineid}/${resolver}/${application}`,
      { headers },
    );
  }

  deleteTokenMtid(
    serial: string,
    application: string,
    mtid: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.delete(
      `${this.baseUrl}token/${serial}/${application}/${mtid}`,
      { headers },
    );
  }
}
