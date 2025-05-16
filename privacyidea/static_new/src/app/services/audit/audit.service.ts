import { computed, Injectable, linkedSignal, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { Sort } from '@angular/material/sort';
import { ContentService } from '../content/content.service';
import { TableUtilsService } from '../table-utils/table-utils.service';

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
  filterValue = signal('');
  filterParams = computed<Record<string, string>>(() => {
    const combinedFilters = [...this.apiFilter, ...this.advancedApiFilter];
    const { filterPairs, remainingFilterText } =
      this.tableUtilsService.parseFilterString(
        this.filterValue()!,
        combinedFilters,
      );
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
  auditResource = httpResource<any>(() => {
    if (this.contentService.routeUrl() !== '/audit') {
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
