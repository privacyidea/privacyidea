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
  timestamp: string;
  source_ip?: string | null;
  client_label?: string | null;
  serial?: string | null;
  transaction_id?: string | null;
  previous_transaction_id?: string | null;
  other_info?: Record<string, unknown> | null;
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

const DEFAULT_PAGE_SIZE = 15;

// Shallow value-equality for the flat string->string filter params record.
function shallowEqualRecord(a: Record<string, string>, b: Record<string, string>): boolean {
  const aKeys = Object.keys(a);
  return aKeys.length === Object.keys(b).length && aKeys.every((key) => a[key] === b[key]);
}

// Filter parameters that the backend matches exactly (see _FILTER_PARAMS in api/authentication_log.py).
const apiFilter = [
  "resolver",
  "uid",
  "realm",
  "username",
  "event_type",
  "source_ip",
  "serial",
  "transaction_id",
  "previous_transaction_id",
  "client_label"
];

// Filters not tied to a table column, reached via the "more filters" control instead of a column header.
const advancedApiFilter: string[] = ["user_role"];

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

  eventTypes = computed<AuthenticationLogEventType[]>(() => this.eventTypesResource.value()?.result?.value ?? []);

  clearFilter(): void {
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: "" }));
  }

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: input.value }));
  }
}
