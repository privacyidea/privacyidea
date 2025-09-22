/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable, linkedSignal, signal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";

import { FilterValue } from "../../core/models/filter_value";

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
  "container_serial",
  "startdate",
  "duration",
  "token_type",
  "user",
  "realm",
  "administrator",
  "action_detail",
  "info",
  "policies",
  "client",
  "user_agent",
  "user_agent_version",
  "privacyidea_server",
  "resolver",
  "container_type"
];
const advancedApiFilter: string[] = [];

export interface AuditServiceInterface {
  apiFilter: string[];
  advancedApiFilter: string[];
  auditFilter: WritableSignal<FilterValue>;
  filterParams: () => Record<string, string>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined>;
  clearFilter(): void;
  handleFilterInput($event: Event): void;
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
  auditFilter = signal(new FilterValue());
  filterParams = computed<Record<string, string>>(() => {
    const allowedFilters = [...this.apiFilter, ...this.advancedApiFilter];
    const filterPairs = Array.from(this.auditFilter().filterMap.entries())
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
    source: () => this.authService.auditPageSize(),
    computation: (pageSize) => (pageSize > 0 ? pageSize : 10)
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.auditFilter(),
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

  clearFilter(): void {
    this.auditFilter.set(this.auditFilter().copyWith({ value: "" }));
  }
  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    this.auditFilter.set(this.auditFilter().copyWith({ value: input.value }));
  }
}
