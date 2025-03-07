import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs/internal/Observable';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';

interface GetTokenParams {
  serial?: string;
  hostname?: string;
  machineid?: string;
  resolver?: string;
  service_id?: string;
  user?: string;
  count?: string;
  rounds?: string;
  page?: number;
  pageSize?: number;
  sortby?: string;
  sortdir?: string;
  application?: string;
}

@Injectable({
  providedIn: 'root',
})
export class MachineService {
  baseUrl: string = environment.proxyUrl + '/machine/';

  constructor(
    private http: HttpClient,
    private localService: LocalService,
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

  splitFilters(filterValue: string) {
    const filterMap: { [key: string]: string } = {};
    const regexp = new RegExp(/\w+:\s\w+((?=\s)|$)/, 'g');
    const matches = filterValue.match(regexp);
    console.log('matches', matches);
    if (matches) {
      matches.forEach((match) => {
        const [key, value] = match.split(': ');
        filterMap[key] = value;
      });
    }

    return filterMap;
  }

  getToken(named: {
    sortby?: string;
    sortdir?: string;
    page?: number;
    pageSize: number;
    currentFilter: string;
    application: 'ssh' | 'offline';
  }): Observable<any> {
    const { sortby, sortdir, currentFilter, page, pageSize, application } =
      named;
    let filterMap: { [key: string]: string } = {};
    if (currentFilter) {
      filterMap = this.splitFilters(currentFilter);
    }
    const {
      serial,
      hostname,
      machineid,
      resolver,
      service_id,
      user,
      count,
      rounds,
    } = filterMap;

    const headers = this.localService.getHeaders();
    let params = new HttpParams();
    if (serial) params = params.set('serial', `*${serial}*`);
    if (hostname) params = params.set('hostname', `*${hostname}*`);
    if (machineid) params = params.set('machineid', `*${machineid}*`);
    if (resolver) params = params.set('resolver', `*${resolver}*`);
    if (page) params = params.set('page', page.toString());
    if (pageSize) params = params.set('pagesize', pageSize.toString());
    if (sortby) params = params.set('sortby', sortby);
    if (sortdir) params = params.set('sortdir', sortdir);
    if (application) params = params.set('application', application);
    if (application === 'ssh') {
      if (service_id) params = params.set('service_id', `*${service_id}*`);
      if (user) params = params.set('user', `*${user}*`);
    } else if (application === 'offline') {
      if (count) params = params.set('count', count);
      if (rounds) params = params.set('rounds', rounds);
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
