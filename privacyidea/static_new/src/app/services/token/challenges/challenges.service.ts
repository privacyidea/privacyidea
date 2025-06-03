import {
  computed,
  Injectable,
  linkedSignal,
  WritableSignal,
} from '@angular/core';
import { Sort } from '@angular/material/sort';
import { httpResource } from '@angular/common/http';
import { TokenService } from '../token.service';
import { LocalService } from '../../local/local.service';
import { TableUtilsService } from '../../table-utils/table-utils.service';
import { ContentService } from '../../content/content.service';
import { PiResponse } from '../../../app.component';

const apiFilter = ['serial', 'transaction_id'];
const advancedApiFilter: string[] = [];

export interface Challenges {
  challenges: Challenge[];
  count: number;
  current: number;
  next?: number;
  prev?: number;
}

export interface Challenge {
  challenge: string;
  data: string;
  expiration: string;
  id: number;
  otp_received: boolean;
  otp_valid: boolean;
  received_count: number;
  serial: string;
  timestamp: string;
  transaction_id: string;
}

@Injectable({
  providedIn: 'root',
})
export class ChallengesService {
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  selectedContent = this.contentService.selectedContent;
  tokenBaseUrl = this.tokenService.tokenBaseUrl;
  filterValue = linkedSignal({
    source: this.selectedContent,
    computation: () => ({}) as Record<string, string>,
  });
  private filterParams = computed(() => {
    const allowedFilters = [...this.apiFilter, ...this.advancedApiFilter];
    const filterPairs = Object.entries(this.filterValue())
      .map(([key, value]) => ({ key, value }))
      .filter(({ key }) => allowedFilters.includes(key));
    return filterPairs.reduce(
      (acc, { key, value }) => {
        if (key === 'serial') {
          acc.serial = `*${value}*`;
        } else {
          acc.params[key] = `*${value}*`;
        }
        return acc;
      },
      { params: {} as Record<string, string>, serial: '' },
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
  challengesResource = httpResource<PiResponse<Challenges>>(() => {
    if (this.selectedContent() !== 'token_challenges') {
      return undefined;
    }
    const { params: filterParams, serial } = this.filterParams();
    const url = serial
      ? `${this.tokenBaseUrl}challenges/${serial}`
      : `${this.tokenBaseUrl}challenges/`;
    return {
      url,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: {
        pagesize: this.pageSize(),
        page: this.pageIndex() + 1,
        ...(this.sort().active && {
          sortby: this.sort().active,
          sortdir: this.sort().direction || 'asc',
        }),
        ...filterParams,
      },
    };
  });

  constructor(
    private tokenService: TokenService,
    private localService: LocalService,
    private tableUtilsService: TableUtilsService,
    private contentService: ContentService,
  ) {}
}
