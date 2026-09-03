/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

import { HttpClient, HttpResourceRef, httpResource } from "@angular/common/http";
import { Injectable, WritableSignal, computed, effect, inject, linkedSignal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { StringUtils } from "@utils/string.utils";
import { Observable } from "rxjs";

export interface AuthenticationLogEntry {
  id: number;
  resolver?: string | null;
  uid?: string | null;
  realm?: string | null;
  username?: string | null;
  user_role?: string | null;
  event_type: string;
  timestamp: string;
  source_ip?: string | null;
  client_label?: string | null;
  serial?: string | null;
  transaction_id?: string | null;
  attempt_id?: string | null;
  other_info?: Record<string, unknown> | null;
  conditional_access_outcomes?: Record<string, unknown>[] | null;
}

export interface AuthenticationLogPage {
  auth_logs: AuthenticationLogEntry[];
  count: number;
  current: number;
  prev: number | null;
  next: number | null;
}

// One classification of an attempt-level statistics result: how many authentication *attempts* ended as
// `event_type`, bucketed over the window. `counts` holds one entry per bin, in bin order and always as long as
// `bins.count`, so a bucket where nothing happened is a 0 rather than a gap and the series charts without realignment.
// `outcome` is an AuthEventOutcome value ("success" | "failure" | "pending"), null for an event type the backend does
// not classify.
export interface AuthenticationEventSeries {
  event_type: string;
  outcome: string | null;
  counts: number[];
  total: number;
}

// Attempt-level statistics over one time window. `events` holds one series per classification *present in the window*:
// a classification no attempt ended with has no series at all, so a missing entry reads as zero. Series come most
// frequent first. `bins.starts` are the inclusive bucket starts, in the same order as every series' `counts`.
export interface AuthenticationLogStatistics {
  window: { start_time: string; end_time: string; total: number };
  bins: { count: number; starts: string[] };
  events: AuthenticationEventSeries[];
}

// One defined authentication-log event type with its outcome class. The authoritative list comes from the backend.
// `outcome` is an AuthEventOutcome value: "success" | "failure" | "pending".
export interface AuthenticationLogEventType {
  name: string;
  outcome: string;
}

const DEFAULT_PAGE_SIZE = 100;

// Shallow value-equality for the flat string->string filter params record.
function shallowEqualRecord(a: Record<string, string>, b: Record<string, string>): boolean {
  const aKeys = Object.keys(a);
  return aKeys.length === Object.keys(b).length && aKeys.every((key) => a[key] === b[key]);
}

// Filter parameters that the backend matches exactly (see _FILTER_PARAMS in api/authentication_log.py).
const apiFilter = [
  "realm",
  "username",
  "event_type",
  "source_ip",
  "serial",
  "transaction_id",
  "attempt_id",
  "client_label"
];

// Filters not tied to a table column, reached via the "more filters" control: the three ca_* ones filter on the entry's
// conditional-access outcomes (see _FILTER_PARAMS in api/authentication_log.py) and are also offered in the Conditional
// access column's menu; resolver and uid have no column either - they identify the same user the username column
// already names - but stay filterable by hand.
const advancedApiFilter: string[] = ["user_role", "resolver", "uid", "ca_action_type", "ca_policy_name", "ca_dry_run"];

export interface AuthenticationLogServiceInterface {
  apiFilter: string[];
  advancedApiFilter: string[];
  authenticationLogFilter: WritableSignal<FilterValue>;
  filterParams: () => Record<string, string>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  sort: WritableSignal<Sort>;
  timestampFrom: WritableSignal<string | null>;
  timestampTo: WritableSignal<string | null>;
  canRead: () => boolean;
  authenticationLogResource: HttpResourceRef<PiResponse<AuthenticationLogPage> | undefined>;
  eventTypesResource: HttpResourceRef<PiResponse<AuthenticationLogEventType[]> | undefined>;
  eventTypes: () => AuthenticationLogEventType[];
  oldestTimestamp: () => string | null;

  fetchStatistics(
    startTime: string,
    endTime: string,
    bins?: number
  ): Observable<PiResponse<AuthenticationLogStatistics>>;

  clearFilter(): void;

  handleFilterInput($event: Event): void;
}

@Injectable()
export class AuthenticationLogService implements AuthenticationLogServiceInterface {
  private readonly http = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  private authenticationLogBaseUrl = environment.proxyUrl + "/authenticationlog/";
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.authenticationLogResource.error(), "authentication log data");
    });
  }

  authenticationLogFilter = signal(new FilterValue());

  // The backend matches these filters exactly, so values are sent verbatim (no wildcard wrapping, unlike the audit
  // log). Value-based equality means adding/clearing a filter *key* with no value (e.g. "username: ") yields the same
  // params object and skips a reload; a changed value still propagates.
  filterParams = computed<Record<string, string>>(
    () => {
      const allowed = [...this.apiFilter, ...this.advancedApiFilter];
      const entries = Array.from(this.authenticationLogFilter().filterMap.entries())
        .filter(([key]) => allowed.includes(key))
        .map(([key, value]) => [key, (value ?? "").toString().trim()] as const)
        .filter(([, value]) => StringUtils.validFilterValue(value));
      return Object.fromEntries(entries) as Record<string, string>;
    },
    { equal: shallowEqualRecord }
  );

  pageSize = signal(DEFAULT_PAGE_SIZE);
  timestampFrom = signal<string | null>(null);
  timestampTo = signal<string | null>(null);
  sort = signal({ active: "timestamp", direction: "desc" } as Sort);

  canRead = computed(() => this.authService.actionAllowed("authentication_log_read"));

  pageIndex = linkedSignal({
    // Keyed on the effective params (filterParams), not the raw filter text, so a value-less key edit does not
    // reset the page (which would itself trigger a reload).
    source: () => ({
      filterParams: this.filterParams(),
      pageSize: this.pageSize(),
      timestampFrom: this.timestampFrom(),
      timestampTo: this.timestampTo(),
      sort: this.sort()
    }),
    // 1-based, matching the API's page param; the mat-paginator binding converts to its own 0-based index.
    computation: () => 1
  });

  authenticationLogResource = httpResource<PiResponse<AuthenticationLogPage>>(() => {
    // Only load on the authentication-log route, and only for a user allowed to read the log.
    if (!this.contentService.onAuthenticationLog() || !this.canRead()) {
      return undefined;
    }
    return {
      url: this.authenticationLogBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        page: this.pageIndex(),
        page_size: this.pageSize(),
        sort_column: this.sort().active,
        sort_order: this.sort().direction || "desc",
        // The WebUI filter is always case-insensitive.
        case_insensitive: true,
        ...(this.timestampFrom() ? { start_time: this.timestampFrom()! } : {}),
        ...(this.timestampTo() ? { end_time: this.timestampTo()! } : {}),
        ...this.filterParams()
      }
    };
  });

  // The defined event types (with outcome) come from the backend so the WebUI does not duplicate the list. Gated like
  // the log itself (route + read right). eventTypes() defaults to [] until loaded / when not allowed.
  eventTypesResource = httpResource<PiResponse<AuthenticationLogEventType[]>>(() => {
    if (!this.contentService.onAuthenticationLog() || !this.canRead()) {
      return undefined;
    }
    return {
      url: this.authenticationLogBaseUrl + "eventtypes",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  eventTypes = computed<AuthenticationLogEventType[]>(() => {
    if (!this.eventTypesResource.hasValue()) return [];
    return this.eventTypesResource.value()?.result?.value ?? [];
  });

  // The single oldest entry (timestamp ascending), used to size the time slider's default window down to the first
  // recorded event. Gated like the log itself (route + read right).
  oldestEntryResource = httpResource<PiResponse<AuthenticationLogPage>>(() => {
    if (!this.contentService.onAuthenticationLog() || !this.canRead()) {
      return undefined;
    }
    return {
      url: this.authenticationLogBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: { page: 1, page_size: 1, sort_column: "timestamp", sort_order: "asc" }
    };
  });

  oldestTimestamp = computed<string | null>(() => {
    if (!this.oldestEntryResource.hasValue()) return null;
    return this.oldestEntryResource.value()?.result?.value?.auth_logs?.[0]?.timestamp ?? null;
  });

  // A one-off read for callers outside the authentication-log route, where the resources above deliberately do not
  // fetch. An Observable rather than an httpResource because the dashboard widget drives the window itself and caches
  // the response in the DashboardDataStore.
  fetchStatistics(
    startTime: string,
    endTime: string,
    bins?: number
  ): Observable<PiResponse<AuthenticationLogStatistics>> {
    return this.http.get<PiResponse<AuthenticationLogStatistics>>(this.authenticationLogBaseUrl + "statistics", {
      headers: this.authService.getHeaders(),
      params: { start_time: startTime, end_time: endTime, ...(bins ? { bins } : {}) }
    });
  }

  clearFilter(): void {
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: "" }));
  }

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: input.value }));
  }
}
