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

import { HttpResourceRef, httpResource } from "@angular/common/http";
import { Injectable, WritableSignal, computed, effect, inject, linkedSignal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { StringUtils } from "@utils/string.utils";

export interface AuthenticationLogEntry {
  id: number;
  resolver?: string | null;
  uid?: string | null;
  realm?: string | null;
  username?: string | null;
  user_role?: string | null;
  event_type: string;
  reason?: string | null;
  timestamp: string;
  source_ip?: string | null;
  client_label?: string | null;
  endpoint?: string | null;
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

// Filter keys the backend matches exactly (see _FILTER_PARAMS in api/authentication_log.py). A key is a *column* of
// the table, which is why it is singular here while the query parameter it is sent as is plural (see apiParamOf).
const apiFilter = [
  "realm",
  "username",
  "event_type",
  "reason",
  "source_ip",
  "serial",
  "transaction_id",
  "attempt_id",
  "client_label",
  "endpoint"
];

// Filters not tied to a table column, reached via the "more filters" control instead of a column header. The three
// ca_* ones filter on the entry's conditional-access outcomes (see _FILTER_PARAMS in api/authentication_log.py): they
// are offered in the Conditional access column's menu, and listed here so they can also be typed in the main filter.
// resolver and uid have no column either - they identify the same user the username column already names - but stay
// filterable by hand.
const advancedApiFilter: string[] = ["user_role", "resolver", "uid", "ca_action_type", "ca_policy_name", "ca_dry_run"];

// The query parameter each filter key is sent as. Every one of these filters takes a comma-separated list of values, so
// the API names them in the plural while a filter key names the single column it matches. ca_dry_run is the exception:
// it is a single boolean, so its name is already the one the API expects.
function apiParamOf(filterKey: string): string {
  return filterKey === "ca_dry_run" ? filterKey : `${filterKey}s`;
}

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
  reasonsResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  reasons: () => string[];
  endpointsResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  endpoints: () => string[];
  oldestTimestamp: () => string | null;

  clearFilter(): void;

  handleFilterInput($event: Event): void;
}

@Injectable()
export class AuthenticationLogService implements AuthenticationLogServiceInterface {
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

  // The backend matches these filters exactly, so values are sent verbatim (no wildcard wrapping, unlike the audit log).
  // Value-based equality so adding/clearing a filter *key* without a value (e.g. "username: ") yields the same
  // effective params object and does NOT re-notify -> no needless reload. A changed value still propagates.
  filterParams = computed<Record<string, string>>(
    () => {
      const allowed = [...this.apiFilter, ...this.advancedApiFilter];
      const entries = Array.from(this.authenticationLogFilter().filterMap.entries())
        .filter(([key]) => allowed.includes(key))
        .map(([key, value]) => [apiParamOf(key), (value ?? "").toString().trim()] as const)
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

  // Why an event came out the way it did: the reason vocabulary, served by the backend for the same reason the event
  // types are - the WebUI filters by it and must not keep a second copy of the list. Gated like the log itself.
  reasonsResource = httpResource<PiResponse<string[]>>(() => {
    if (!this.contentService.onAuthenticationLog() || !this.canRead()) {
      return undefined;
    }
    return {
      url: this.authenticationLogBaseUrl + "reasons",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  reasons = computed<string[]>(() => {
    if (!this.reasonsResource.hasValue()) return [];
    return this.reasonsResource.value()?.result?.value ?? [];
  });

  // The endpoints an authentication can arrive at, served by the backend like the two vocabularies above. A closed
  // list of request paths, so the endpoint filter is a selection of them rather than a path typed by hand. Gated like
  // the log itself.
  endpointsResource = httpResource<PiResponse<string[]>>(() => {
    if (!this.contentService.onAuthenticationLog() || !this.canRead()) {
      return undefined;
    }
    return {
      url: this.authenticationLogBaseUrl + "endpoints",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  endpoints = computed<string[]>(() => {
    if (!this.endpointsResource.hasValue()) return [];
    return this.endpointsResource.value()?.result?.value ?? [];
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

  clearFilter(): void {
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: "" }));
  }

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: input.value }));
  }
}
