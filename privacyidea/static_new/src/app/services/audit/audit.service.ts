import { computed, Injectable, linkedSignal, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { Sort } from '@angular/material/sort';
import { ContentService } from '../content/content.service';
import { TableUtilsService } from '../table-utils/table-utils.service';
import { PiResponse } from '../../app.component';

export interface Audit {
  auditcolumns: string[];
  auditdata: AuditData[];
  count: number;
  current: number;
  next?: number;
  prev?: number;
}

export interface AuditData {
  action?: string;
  action_detail?: string;
  administrator?: string;
  authentication?: string;
  clearance_level?: string;
  client?: string;
  container_serial?: string;
  container_type?: string;
  date?: string;
  duration?: number;
  info?: string;
  log_level?: any;
  missing_line?: string;
  number?: number;
  policies?: any;
  privacyidea_server?: string;
  realm?: any;
  resolver?: any;
  serial?: string;
  sig_check?: string;
  startdate?: string;
  success?: boolean;
  thread_id?: string;
  token_type?: any;
  user?: any;
  user_agent?: string;
  user_agent_version?: string;
}

const apiFilter = [
  'action',
  'success',
  'authentication',
  'serial',
  'date',
  'startdate',
  'duration',
  'token_type',
  'user',
  'realm',
  'administrator',
  'action_call',
  'info',
  'privacyidea_server',
  'client',
  'user_agent',
  'user_agent_version',
  'policies',
  'resolver',
  'container_serial',
  'container_type',
];
const advancedApiFilter: string[] = [];

@Injectable({
  providedIn: 'root',
})
export class AuditService {
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  auditBaseUrl = environment.proxyUrl + '/audit/';
  filterValue = signal({} as Record<string, string>);
  filterParams = computed<Record<string, string>>(() => {
    const allowedFilters = [...this.apiFilter, ...this.advancedApiFilter];
    const filterPairs = Object.entries(this.filterValue())
      .map(([key, value]) => ({ key, value }))
      .filter(({ key }) => allowedFilters.includes(key));
    if (filterPairs.length === 0) {
      return {};
    }
    return filterPairs.reduce(
      (acc, { key, value }) => ({
        ...acc,
        [key]: `*${value}*`,
      }),
      {} as Record<string, string>,
    );
  });
  pageSize = linkedSignal({
    source: this.filterValue,
    computation: () => 10,
  });
  sort = linkedSignal({
    source: () => ({
      pageSize: this.pageSize(),
      selectedContent: this.contentService.selectedContent(),
    }),
    computation: () => {
      return { active: 'serial', direction: 'asc' } as Sort;
    },
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize(),
      selectedContent: this.contentService.selectedContent(),
    }),
    computation: () => 0,
  });
  auditResource = httpResource<PiResponse<Audit>>(() => {
    if (
      this.contentService.routeUrl() !== '/audit' &&
      this.contentService.selectedContent() !== 'audit'
    ) {
      return undefined;
    }
    return {
      url: this.auditBaseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: {
        page_size: this.pageSize(),
        page: this.pageIndex(),
        ...this.filterParams(),
      },
    };
  });

  constructor(
    private localService: LocalService,
    private contentService: ContentService,
    private tableUtilsService: TableUtilsService,
  ) {}
}
