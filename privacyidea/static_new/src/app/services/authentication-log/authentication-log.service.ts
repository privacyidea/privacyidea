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

import { HttpClient, HttpParams, HttpResourceRef, httpResource } from "@angular/common/http";
import { Injectable, WritableSignal, computed, effect, inject, linkedSignal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { StringUtils } from "@utils/string.utils";
import { Observable, catchError, throwError } from "rxjs";

export interface AuthenticationLogEntry {
  id: number;
  resolver?: string | null;
  uid?: string | null;
  realm?: string | null;
  username?: string | null;
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

const DEFAULT_PAGE_SIZE = 15;

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

const advancedApiFilter: string[] = [];

export interface AuthenticationLogServiceInterface {
  apiFilter: string[];
  advancedApiFilter: string[];
  authenticationLogFilter: WritableSignal<FilterValue>;
  filterParams: () => Record<string, string>;
  pageSize: WritableSignal<number>;
  pageIndex: WritableSignal<number>;
  sort: WritableSignal<Sort>;
  start: WritableSignal<string | null>;
  end: WritableSignal<string | null>;
  includeOwn: WritableSignal<boolean>;
  canRead: () => boolean;
  canDelete: () => boolean;
  authenticationLogResource: HttpResourceRef<PiResponse<AuthenticationLogPage> | undefined>;

  clearFilter(): void;

  handleFilterInput($event: Event): void;

  deleteOlderThan(days: number): Observable<PiResponse<number>>;
}

@Injectable()
export class AuthenticationLogService implements AuthenticationLogServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

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
  filterParams = computed<Record<string, string>>(() => {
    const allowed = [...this.apiFilter, ...this.advancedApiFilter];
    const entries = Array.from(this.authenticationLogFilter().filterMap.entries())
      .filter(([key]) => allowed.includes(key))
      .map(([key, value]) => [key, (value ?? "").toString().trim()] as const)
      .filter(([, value]) => StringUtils.validFilterValue(value));
    return Object.fromEntries(entries) as Record<string, string>;
  });

  pageSize = signal(DEFAULT_PAGE_SIZE);
  start = signal<string | null>(null);
  end = signal<string | null>(null);
  includeOwn = signal(false);
  sort = signal({ active: "timestamp", direction: "desc" } as Sort);

  canRead = computed(() => this.authService.actionAllowed("authentication_log_read"));
  canDelete = computed(() => this.authService.actionAllowed("authentication_log_delete"));

  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.authenticationLogFilter(),
      pageSize: this.pageSize(),
      start: this.start(),
      end: this.end(),
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
        ...(this.start() ? { start: this.start()! } : {}),
        ...(this.end() ? { end: this.end()! } : {}),
        ...(this.includeOwn() ? { include_own: "1" } : {}),
        ...this.filterParams()
      }
    };
  });

  clearFilter(): void {
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: "" }));
  }

  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    this.authenticationLogFilter.set(this.authenticationLogFilter().copyWith({ value: input.value }));
  }

  // Cleanup: delete every entry older than *days* days, i.e. with a timestamp at or before that cutoff. Passing 0 is
  // a deliberate "delete the whole log"; a non-finite or negative value is rejected to guard against an empty/NaN input.
  deleteOlderThan(days: number): Observable<PiResponse<number>> {
    if (!this.canDelete()) {
      const message = $localize`You are not allowed to delete authentication log entries.`;
      this.notificationService.error(message);
      return throwError(() => new Error(message));
    }
    if (!Number.isFinite(days) || days < 0) {
      const message = $localize`Invalid number of days for the authentication log cleanup.`;
      this.notificationService.error(message);
      return throwError(() => new Error(message));
    }
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    const params = new HttpParams().set("end", cutoff);
    return this.http
      .delete<PiResponse<number>>(this.authenticationLogBaseUrl, {
        headers: this.authService.getHeaders(),
        params
      })
      .pipe(
        catchError((error) => {
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to delete authentication log entries. ${message}`);
          return throwError(() => error);
        })
      );
  }
}
