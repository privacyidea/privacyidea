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
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";

import { PiResponse } from "@app/app.component";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { Observable } from "rxjs";

import { environment } from "@env/environment";
import { CaConnectors } from "@services/ca-connector/ca-connector.service";

export interface NodeInfo {
  name: string;
  uuid: string;
}

export interface DeleteUserCacheResult {
  status: boolean;
  deleted: number;
}

export type CertificateStatus = "ok" | "warning" | "critical" | "expired" | "error";

export interface CertificateHealthEntry {
  source: string;
  name: string;
  host: string | null;
  tls_mode: string | null;
  subject: string | null;
  issuer: string | null;
  not_after: string | null;
  days_remaining: number | null;
  error: string | null;
  status: CertificateStatus;
}

export interface ResolverTimingEntry {
  labels: { resolver: string; resolver_type: string; op: string };
  count: number;
  avg: number | null;
  p50: number | null;
  p95: number | null;
  max: number | null;
  buckets: [number, number][];
}

export interface NotificationChannelEntry {
  key: string;
  ok: number;
  failed: number;
  error: number;
  total: number;
  avg?: number;
  p50?: number;
  p95?: number;
  max?: number;
  duration_count?: number;
}

export interface NotificationDeliveryHealth {
  push: NotificationChannelEntry[];
  sms: NotificationChannelEntry[];
  email: NotificationChannelEntry[];
  since_seconds: number;
}

/**
 * Frontend-supplied default values that accompany the system config response.
 * Backend `GET /system/` returns `result.value` as `Record<string, string>`;
 * `result.init` holds additional UI defaults (e.g. allowed hash libs, TOTP
 * step choices) which may be extended over time.
 */
export interface SystemConfigInit {
  hashlibs?: string[];
  totpSteps?: number | number[];
  smsProviders?: string[];

  [key: string]: unknown;
}

/**
 * Shape of the `GET /system/` response. Mirrors `PiResponse` but
 * declares `result` explicitly to surface the WebUI-only `init` field.
 */
export interface SystemConfigResponse {
  id: number;
  jsonrpc: string;
  detail: unknown;
  result?: {
    authentication?: "CHALLENGE" | "POLL" | "PUSH" | "ACCEPT" | "REJECT";
    status: boolean;
    value?: Record<string, string>;
    init?: SystemConfigInit;
    error?: { code: number; message: string };
  };
  signature: string;
  time: number;
  version: string;
  versionnumber: string;
}

export interface SystemServiceInterface {
  systemConfigResource: HttpResourceRef<SystemConfigResponse | undefined>;
  radiusServerResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  caConnectorResource?: HttpResourceRef<PiResponse<CaConnectors> | undefined>;
  caConnectors?: WritableSignal<CaConnectors>;
  nodesResource: HttpResourceRef<PiResponse<NodeInfo[]> | undefined>;
  systemConfig: Signal<Record<string, string>>;
  systemConfigInit: Signal<SystemConfigInit>;
  nodes: Signal<NodeInfo[]>;
  radiusServers: Signal<string[]>;

  saveSystemConfig(config: Record<string, unknown>): Observable<PiResponse<Record<string, "insert" | "update">>>;

  deleteSystemConfig(key: string): Observable<PiResponse<boolean>>;

  deleteUserCache(): Observable<PiResponse<DeleteUserCacheResult>>;

  getDocumentation(): Observable<string>;

  getCertificateHealth(): Observable<PiResponse<CertificateHealthEntry[]>>;

  getResolverTiming(sinceSeconds?: number): Observable<PiResponse<ResolverTimingEntry[]>>;

  getNotificationDelivery(sinceSeconds?: number): Observable<PiResponse<NotificationDeliveryHealth>>;
}

@Injectable()
export class SystemService implements SystemServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly http = inject(HttpClient);

  private readonly systemBaseUrl = environment.proxyUrl + "/system/";
  private onAllowedRoutes = computed(() => {
    return (
      this.contentService.onTokenEnrollmentLikely() ||
      this.contentService.onConfigurationSystem() ||
      this.contentService.onConfigurationTokenTypes()
    );
  });

  systemConfigResource = httpResource<SystemConfigResponse>(() => {
    // Only load system config on enrollment or wizard routes.
    if (!this.onAllowedRoutes()) {
      return undefined;
    }

    return {
      url: this.systemBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  radiusServerResource = httpResource<PiResponse<string[]>>(() => {
    // Do not load RADIUS server details if the action is not allowed.
    if (!this.authService.actionAllowed("enrollRADIUS")) {
      return undefined;
    }
    // Only load RADIUS server details on enrollment or token wizard routes.
    if (!this.onAllowedRoutes()) {
      return undefined;
    }

    return {
      url: this.systemBaseUrl + "names/radius",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  caConnectorResource = httpResource<PiResponse<CaConnectors>>(() => {
    // Do not load CA connectors details if the action is not allowed.
    if (!this.authService.actionAllowed("enrollCERTIFICATE")) {
      return undefined;
    }
    // Only load CA connectors on enrollment or token wizard routes.
    if (!this.onAllowedRoutes()) {
      return undefined;
    }

    return {
      url: environment.proxyUrl + "/system/names/caconnector",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  caConnectors: WritableSignal<CaConnectors> = linkedSignal({
    source: () => ({
      value: this.caConnectorResource.hasValue() ? this.caConnectorResource.value() : undefined,
      isLoading: this.caConnectorResource.isLoading(),
      error: this.caConnectorResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return [];
      const caConnectors = source.value?.result?.value;
      if (!caConnectors) return source.isLoading ? (previous?.value ?? []) : [];
      return caConnectors;
    }
  });
  nodesResource = httpResource<PiResponse<NodeInfo[]>>(() => {
    if (
      !this.contentService.onConfigurationPeriodicTasks() &&
      !this.contentService.onConfigurationSystem() &&
      !this.contentService.onUserRealms()
    ) {
      return undefined;
    }
    return {
      url: this.systemBaseUrl + "nodes",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  systemConfig = computed<Record<string, string>>(() => {
    if (!this.systemConfigResource.hasValue()) return {};
    return this.systemConfigResource.value()?.result?.value ?? {};
  });
  systemConfigInit = computed<SystemConfigInit>(() => {
    if (!this.systemConfigResource.hasValue()) return {};
    return this.systemConfigResource.value()?.result?.init ?? {};
  });
  nodes = computed<NodeInfo[]>(() => {
    if (!this.nodesResource.hasValue()) return [];
    return this.nodesResource.value()?.result?.value ?? [];
  });
  radiusServers = computed(() => {
    if (!this.radiusServerResource.hasValue()) return [];
    return this.radiusServerResource.value()?.result?.value ?? [];
  });

  saveSystemConfig(config: Record<string, unknown>): Observable<PiResponse<Record<string, "insert" | "update">>> {
    return this.http.post<PiResponse<Record<string, "insert" | "update">>>(this.systemBaseUrl + "setConfig", config, {
      headers: this.authService.getHeaders()
    });
  }

  deleteSystemConfig(key: string): Observable<PiResponse<boolean>> {
    return this.http.delete<PiResponse<boolean>>(`${this.systemBaseUrl}${encodeURIComponent(key)}`, {
      headers: this.authService.getHeaders()
    });
  }

  deleteUserCache(): Observable<PiResponse<DeleteUserCacheResult>> {
    return this.http.delete<PiResponse<DeleteUserCacheResult>>(`${this.systemBaseUrl}user-cache`, {
      headers: this.authService.getHeaders()
    });
  }

  getDocumentation(): Observable<string> {
    return this.http.get(`${this.systemBaseUrl}documentation`, {
      headers: this.authService.getHeaders(),
      responseType: "text"
    });
  }

  getCertificateHealth(): Observable<PiResponse<CertificateHealthEntry[]>> {
    return this.http.get<PiResponse<CertificateHealthEntry[]>>(`${this.systemBaseUrl}health/certificates`, {
      headers: this.authService.getHeaders()
    });
  }

  getResolverTiming(sinceSeconds = 3600): Observable<PiResponse<ResolverTimingEntry[]>> {
    return this.http.get<PiResponse<ResolverTimingEntry[]>>(`${this.systemBaseUrl}health/resolver_timing`, {
      headers: this.authService.getHeaders(),
      params: { since_seconds: sinceSeconds }
    });
  }

  getNotificationDelivery(sinceSeconds = 3600): Observable<PiResponse<NotificationDeliveryHealth>> {
    return this.http.get<PiResponse<NotificationDeliveryHealth>>(`${this.systemBaseUrl}health/notification_delivery`, {
      headers: this.authService.getHeaders(),
      params: { since_seconds: sinceSeconds }
    });
  }
}
