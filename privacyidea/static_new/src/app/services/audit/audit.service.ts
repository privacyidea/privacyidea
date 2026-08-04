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
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { FilterableTableService, FilterableTableServiceInterface } from "@services/table-utils/filterable-table-service";
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

export interface AuditServiceInterface extends FilterableTableServiceInterface {
  auditResource: HttpResourceRef<PiResponse<Audit> | undefined>;
  isDownloading: WritableSignal<boolean>;

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

  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.activeFilter(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: () => 1
  });

  sort = signal({ active: "serial", direction: "asc" } as Sort);

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

  isDownloading = signal(false);

  constructor() {
    super();
    effect(() => {
      this.notificationService.handleResourceError(this.auditResource.error(), "audit data");
    });
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
    const params = new HttpParams({ fromObject: this.filterParams() });
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
          this.notificationService.error($localize`Failed to download audit log.`);
        }
      });
  }
}
