import { httpResource, HttpResourceRef } from '@angular/common/http';
import {
  computed,
  inject,
  Injectable,
  linkedSignal,
  signal,
  WritableSignal,
} from '@angular/core';
import { Sort } from '@angular/material/sort';
import { PiResponse } from '../../../app.component';
import {
  ContentService,
  ContentServiceInterface,
} from '../../content/content.service';
import { LocalService, LocalServiceInterface } from '../../local/local.service';
import {
  TableUtilsService,
  TableUtilsServiceInterface,
} from '../../table-utils/table-utils.service';
import { TokenService, TokenServiceInterface } from '../token.service';

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

export interface ChallengesServiceInterface {
  apiFilter: string[];
  advancedApiFilter: string[];
  selectedContent: WritableSignal<string>;
  filterValue: WritableSignal<Record<string, string>>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  sort: WritableSignal<Sort>;
  challengesResource: HttpResourceRef<PiResponse<Challenges> | undefined>;
}

@Injectable({
  providedIn: 'root',
})
export class ChallengesService implements ChallengesServiceInterface {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly tableUtilsService: TableUtilsServiceInterface =
    inject(TableUtilsService);
  private readonly contentService: ContentServiceInterface =
    inject(ContentService);

  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  selectedContent = this.contentService.selectedContent;
  tokenBaseUrl = this.tokenService.tokenBaseUrl;
  filterValue = linkedSignal({
    source: this.contentService.routeUrl,
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
    source: this.contentService.routeUrl,
    computation: () => 10,
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl(),
    }),
    computation: () => 0,
  });
  sort = signal({ active: 'timestamp', direction: 'asc' } as Sort);
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
}
