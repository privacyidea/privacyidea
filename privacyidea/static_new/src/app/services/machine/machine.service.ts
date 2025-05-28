import { HttpClient, HttpParams, httpResource } from '@angular/common/http';
import {
  computed,
  Injectable,
  linkedSignal,
  signal,
  WritableSignal,
} from '@angular/core';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { TableUtilsService } from '../table-utils/table-utils.service';
import { Sort } from '@angular/material/sort';
import { Observable } from 'rxjs';
import { PageEvent } from '@angular/material/paginator';
import { ContentService } from '../content/content.service';
import { PiResponse } from '../../app.component';

type TokenApplications = TokenApplication[];

export interface TokenApplication {
  application: string;
  id: number;
  serial: string;
  machine_id?: any;
  resolver?: any;
  type: string;
  options: {
    service_id?: string;
    user?: string;
  };
}

@Injectable({
  providedIn: 'root',
})
export class MachineService {
  baseUrl = environment.proxyUrl + '/machine/';
  sshApiFilter = ['serial', 'service_id'];
  sshAdvancedApiFilter = ['hostname', 'machineid & resolver'];
  offlineApiFilter = ['serial', 'count', 'rounds'];
  offlineAdvancedApiFilter = ['hostname', 'machineid & resolver'];
  selectedContent = this.contentService.selectedContent;
  selectedApplicationType = signal<'ssh' | 'offline'>('ssh');
  pageSize = linkedSignal({
    source: this.selectedApplicationType,
    computation: () => 10,
  });
  filterValue = linkedSignal({
    source: this.selectedApplicationType,
    computation: () => '',
  });
  private filterParams = computed(() => {
    let combined =
      this.selectedApplicationType() === 'ssh'
        ? [...this.sshApiFilter, ...this.sshAdvancedApiFilter]
        : [...this.offlineApiFilter, ...this.offlineAdvancedApiFilter];
    let { filterPairs } = this.tableUtilsService.parseFilterString(
      this.filterValue(),
      combined,
    );
    let params: any = {};
    filterPairs.forEach(({ key, value }) => {
      if (['serial'].includes(key)) {
        params[key] = `*${value}*`;
      }
      if (['hostname', 'machineid', 'resolver'].includes(key)) {
        params[key] = value;
      }
      if (
        this.selectedApplicationType() === 'ssh' &&
        ['service_id'].includes(key)
      ) {
        params[key] = `*${value}*`;
      }
      if (
        this.selectedApplicationType() === 'offline' &&
        ['count', 'rounds'].includes(key)
      ) {
        params[key] = value;
      }
    });
    return params;
  });
  sort = linkedSignal({
    source: this.selectedApplicationType,
    computation: () => ({ active: 'serial', direction: 'asc' }) as Sort,
  });
  pageIndex = linkedSignal({
    source: () => ({
      application: this.selectedApplicationType(),
      filter: this.filterValue(),
      sort: this.sort(),
    }),
    computation: () => 0,
  });
  tokenApplicationResource = httpResource<PiResponse<TokenApplications>>(() => {
    if (this.selectedContent() !== 'token_applications') {
      return undefined;
    }
    const params = {
      application: this.selectedApplicationType(),
      page: this.pageIndex() + 1,
      pagesize: this.pageSize(),
      sortby: this.sort()?.active || 'serial',
      sortdir: this.sort()?.direction || 'asc',
      ...this.filterParams(),
    };
    console.log('Params:', params);
    return {
      url: this.baseUrl + 'token',
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: params,
    };
  });
  tokenApplications: WritableSignal<TokenApplications> = linkedSignal({
    source: this.tokenApplicationResource.value,
    computation: (tokenApplicationResource, previous) =>
      tokenApplicationResource?.result?.value ?? previous?.value ?? [],
  });

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
    private contentService: ContentService,
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

  onPageEvent(event: PageEvent) {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  onSortEvent($event: Sort) {
    this.sort.set($event);
  }
}
