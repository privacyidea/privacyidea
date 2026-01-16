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
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";

import { FilterValue } from "../../core/models/filter_value";
import { StringUtils } from "../../utils/string.utils";
import { Sort } from "@angular/material/sort";

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

const apiFilterKeyMap: Record<string, string> = {
  action: "action",
  success: "success",
  authentication: "authentication",
  serial: "serial",
  container_serial: "container_serial",
  startdate: "startdate",
  duration: "duration",
  token_type: "token_type",
  user: "user",
  realm: "realm",
  administrator: "administrator",
  action_detail: "action_detail",
  info: "info",
  policies: "policies",
  client: "client",
  user_agent: "user_agent",
  user_agent_version: "user_agent_version",
  privacyidea_server: "privacyidea_server",
  resolver: "resolver",
  container_type: "container_type"
};

const advancedApiFilter: string[] = [];

export interface AuditServiceInterface {
  apiFilterKeyMap: Record<string, string>;
  apiFilter: string[];
  advancedApiFilter: string[];
  auditFilter: WritableSignal<FilterValue>;
  filterParams: () => Record<string, string>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined>;
  sort: WritableSignal<Sort>;

  clearFilter(): void;

  handleFilterInput($event: Event): void;
}

@Injectable({
  providedIn: "root"
})
export class AuditService implements AuditServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  sort = signal({ active: "serial", direction: "asc" } as Sort);

  readonly apiFilter = apiFilter;
  readonly apiFilterKeyMap = apiFilterKeyMap;
  readonly advancedApiFilter = advancedApiFilter;

  auditFilter = signal(new FilterValue());

  filterParams = computed<Record<string, string>>(() => {
    const allowed = [...this.apiFilter, ...this.advancedApiFilter];

    const entries = Array.from(this.auditFilter().filterMap.entries())
      .filter(([key]) => allowed.includes(key))
      .map(([key, value]) => {
        const v = (value ?? "").toString().trim();
        return [key, v ? `*${v}*` : v] as const;
      })
      .filter(([, v]) => StringUtils.validFilterValue(v));

    return Object.fromEntries(entries) as Record<string, string>;
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
    computation: () => 1
  });

  private auditBaseUrl = environment.proxyUrl + "/audit/";
  auditResource = httpResource<PiResponse<Audit>>(() => {
    // Only load audit logs on the audit route.
    if (!this.contentService.onAudit()) {
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
