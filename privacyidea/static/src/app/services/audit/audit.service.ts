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

import { HttpClient, HttpParams, httpResource, HttpResourceRef } from "@angular/common/http";
import { effect, inject, Injectable, linkedSignal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { AuditDownloadDialogComponent } from "@components/logs/audit/audit-download-dialog/audit-download-dialog.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { parseFilterTimestamp } from "@utils/date-format.utils";
import { splitExactMatch } from "@utils/filter.utils";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import {
  FilterableTableService,
  FilterableTableServiceInterface
} from "@services/table-utils/filterable-table-service";
import { finalize, Observable, Subscription } from "rxjs";

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
  log_level?: string;
  missing_line?: string;
  number?: number;
  policies?: string;
  privacyidea_server?: string;
  realm?: string;
  resolver?: string;
  serial?: string;
  sig_check?: string;
  startdate?: string;
  success?: boolean;
  thread_id?: string;
  token_type?: string;
  user?: string;
  user_agent?: string;
  user_agent_version?: string;
}

const apiFilterKeys = [
  "action",
  "success",
  "authentication",
  "serial",
  "container_serial",
  "date",
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

// An emptied or removed chip drops the bound, an unparsable edit in progress keeps the previous one.
function boundFromChip(chip: string | undefined, previous: string | null | undefined): string | null {
  if (!chip?.trim()) {
    return null;
  }
  return parseFilterTimestamp(chip) ?? previous ?? null;
}

// A startdate or date value with a "/" is an ISO 8601 time interval "<start>/<end>", either end may be empty. Any other
// value is a text filter. A leading "=" has no meaning for an interval.
function timeInterval(value: string | undefined): { start: string; end: string } | null {
  const text = splitExactMatch((value ?? "").trim()).text;
  const slash = text.indexOf("/");
  if (slash < 0) {
    return null;
  }
  return { start: text.slice(0, slash), end: text.slice(slash + 1) };
}

const apiFilterKeyMap: Record<string, string> = {
  action: "action",
  success: "success",
  authentication: "authentication",
  serial: "serial",
  container_serial: "container_serial",
  date: "date",
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

export interface AuditServiceInterface extends FilterableTableServiceInterface {
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined>;
  isDownloading: WritableSignal<boolean>;
  timestampFrom: WritableSignal<string | null>;
  timestampTo: WritableSignal<string | null>;
  rangeTimeMode: WritableSignal<boolean>;

  downloadCSV(): void;

  fetchAuditPage(params: Record<string, string | number>): Observable<PiResponse<Audit>>;
}

@Injectable()
export class AuditService extends FilterableTableService implements AuditServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly http = inject(HttpClient);
  readonly apiFilterKeys = apiFilterKeys;
  override readonly apiFilterKeyMap = apiFilterKeyMap;

  readonly activeFilter = signal(new FilterValue());

  pageSize = linkedSignal({
    source: () => this.authService.auditPageSize(),
    computation: (pageSize) => (pageSize > 0 ? pageSize : 10)
  });

  // The time range sent as the startdate interval. The startdate chip in the filter text carries it as
  // "<start>/<end>", so a typed edit of a half moves its bound, an emptied half drops it and an unparsable edit in
  // progress keeps the last one. A startdate chip without "/" is a text filter and no range. The chip is the source of
  // truth: every filter change re-reads it, so a bound set without its chip does not outlive the next filter change.
  // The range picker and the date cell filter write signals and chip together.
  timestampFrom = linkedSignal<string | undefined, string | null>({
    source: () => this.activeFilter().getValueOfKey("startdate"),
    computation: (chip, previous) => {
      const interval = timeInterval(chip);
      return interval ? boundFromChip(interval.start, previous?.value) : null;
    }
  });
  timestampTo = linkedSignal<string | undefined, string | null>({
    source: () => this.activeFilter().getValueOfKey("startdate"),
    computation: (chip, previous) => {
      const interval = timeInterval(chip);
      return interval ? boundFromChip(interval.end, previous?.value) : null;
    }
  });

  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.activeFilter(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl(),
      timestampFrom: this.timestampFrom(),
      timestampTo: this.timestampTo()
    }),
    computation: () => 1
  });

  sort = signal({ active: "serial", direction: "asc" } as Sort);

  private auditBaseUrl = environment.proxyUrl + "/audit/";
  auditResource = httpResource<PiResponse<Audit>>(() => {
    if (!this.contentService.onAudit() || !this.authService.actionAllowed("auditlog")) {
      return undefined;
    }

    return {
      url: this.auditBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        page_size: this.pageSize(),
        page: this.pageIndex(),
        ...this.requestFilterParams()
      }
    };
  });

  isDownloading = signal(false);

  // The "Time" checkbox of the range picker: off applies whole days on click, on picks a time on a clock for each
  // clicked day. Kept here so it survives leaving and reopening the audit log within the session.
  rangeTimeMode = signal(false);

  constructor() {
    super();
    effect(() => {
      this.notificationService.handleResourceError(this.auditResource.error(), "audit data");
    });
  }

  // The filter parameters of search and download. A startdate interval chip goes out as "<fromIso>/<toIso>" in UTC with
  // open ends left empty, or not at all when neither bound is set, instead of the wildcard-wrapped chip text. A typed
  // date interval goes out trimmed and without wildcards, the backend checks its bounds.
  private requestFilterParams(): Record<string, string> {
    const params = { ...this.filterParams() };
    const dateInterval = timeInterval(this.activeFilter().getValueOfKey("date"));
    if (dateInterval) {
      params["date"] = `${dateInterval.start.trim()}/${dateInterval.end.trim()}`;
    }
    if (timeInterval(this.activeFilter().getValueOfKey("startdate"))) {
      delete params["startdate"];
      const fromIso = this.timestampFrom();
      const toIso = this.timestampTo();
      if (fromIso || toIso) {
        params["startdate"] = `${fromIso ?? ""}/${toIso ?? ""}`;
      }
    }
    return params;
  }

  downloadCSV(): void {
    if (this.isDownloading()) {
      return;
    }

    this.dialogService
      .openDialog({
        component: AuditDownloadDialogComponent
      })
      .afterClosed()
      .subscribe((result) => {
        if (result) {
          this.executeDownload();
        }
      });
  }

  fetchAuditPage(params: Record<string, string | number>): Observable<PiResponse<Audit>> {
    return this.http.get<PiResponse<Audit>>(this.auditBaseUrl, {
      headers: this.authService.getHeaders(),
      params
    });
  }

  private downloadSubscription?: Subscription;
  private executeDownload(): void {
    this.isDownloading.set(true);
    const params = new HttpParams({ fromObject: this.requestFilterParams() });
    this.downloadSubscription = this.http
      .get(this.auditBaseUrl + "audit.csv", {
        headers: this.authService.getHeaders(),
        params,
        responseType: "text"
      })
      .pipe(finalize(() => this.isDownloading.set(false)))
      .subscribe({
        next: (data) => {
          const blob = new Blob([data], { type: "text/csv" });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "audit.csv";
          a.click();
          window.URL.revokeObjectURL(url);
        },
        error: () => {
          this.notificationService.error($localize`:@@audit.failedDownload:Failed to download audit log.`);
        }
      });
  }
}
