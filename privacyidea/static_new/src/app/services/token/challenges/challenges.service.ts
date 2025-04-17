import { computed, Injectable, linkedSignal } from '@angular/core';
import { Sort } from '@angular/material/sort';
import { httpResource } from '@angular/common/http';
import { TokenService } from '../token.service';
import { LocalService } from '../../local/local.service';
import { TableUtilsService } from '../../table-utils/table-utils.service';

const apiFilter = ['serial', 'transaction_id'];
const advancedApiFilter: string[] = [];

@Injectable({
  providedIn: 'root',
})
export class ChallengesService {
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  selectedContent = this.tokenService.selectedContent;
  tokenBaseUrl = this.tokenService.tokenBaseUrl;
  filterValue = linkedSignal({
    source: this.selectedContent,
    computation: () => '',
  });
  private filterParams = computed(() => {
    const combined = [...this.apiFilter, ...this.advancedApiFilter];
    const { filterPairs } = this.tableUtilsService.parseFilterString(
      this.filterValue(),
      combined,
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
    source: this.selectedContent,
    computation: () => 10,
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize(),
      selectedContent: this.selectedContent(),
    }),
    computation: () => 0,
  });
  sort = linkedSignal({
    source: () => ({
      pageSize: this.pageSize(),
      selectedContent: this.selectedContent(),
    }),
    computation: () => {
      return { active: 'timestamp', direction: 'asc' } as Sort;
    },
  });
  challengesResource = httpResource<any>(() => ({
    url: this.tokenBaseUrl + 'challenges/',
    method: 'GET',
    headers: this.localService.getHeaders(),
    params: {
      pagesize: this.pageSize(),
      page: this.pageIndex() + 1,
      ...(this.sort().active && {
        sortby: this.sort().active,
        sortdir: this.sort().direction || 'asc',
      }),
      ...this.filterParams(),
    },
  }));

  constructor(
    private tokenService: TokenService,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
  ) {}
}
