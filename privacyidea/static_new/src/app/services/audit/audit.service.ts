import { httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable, linkedSignal, signal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../app.routes";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";

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
  "action",
  "success",
  "authentication",
  "serial",
  "date",
  "startdate",
  "duration",
  "token_type",
  "user",
  "realm",
  "administrator",
  "action_call",
  "info",
  "privacyidea_server",
  "client",
  "user_agent",
  "user_agent_version",
  "policies",
  "resolver",
  "container_serial",
  "container_type"
];
const advancedApiFilter: string[] = [];

export interface AuditServiceInterface {
  apiFilter: string[];
  advancedApiFilter: string[];
  filterValue: WritableSignal<Record<string, string>>;
  filterParams: () => Record<string, string>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined>;
}

@Injectable({
  providedIn: "root"
})
export class AuditService implements AuditServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);

  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  private auditBaseUrl = environment.proxyUrl + "/audit/";
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
        [key]: `*${value}*`
      }),
      {} as Record<string, string>
    );
  });
  pageSize = linkedSignal({
    source: this.filterValue,
    computation: () => this.authService.auditPageSize()
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: () => 0
  });
  auditResource = httpResource<PiResponse<Audit>>(() => {
    if (this.contentService.routeUrl() !== ROUTE_PATHS.AUDIT) {
      return undefined;
    }
    return {
      url: this.auditBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        page_size: this.pageSize(),
        page: this.pageIndex(),
        ...this.filterParams()
      }
    };
  });
}
