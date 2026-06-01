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

export interface SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
  radiusServerResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  caConnectorResource?: HttpResourceRef<any>;
  caConnectors?: WritableSignal<CaConnectors>;
  nodesResource: HttpResourceRef<PiResponse<NodeInfo[]> | undefined>;
  systemConfig: Signal<Record<string, string>>;
  systemConfigInit: Signal<any>;
  nodes: Signal<NodeInfo[]>;
  radiusServers: Signal<string[]>;

  saveSystemConfig(config: Record<string, unknown>): Observable<PiResponse<Record<string, "insert" | "update">>>;
  deleteSystemConfig(key: string): Observable<PiResponse<boolean>>;
  deleteUserCache(): Observable<PiResponse<DeleteUserCacheResult>>;
  // No backend route exists for this and it is currently unused, so the type is unknown.
  loadSmtpIdentifiers(): Observable<PiResponse<any>>;
  getDocumentation(): Observable<string>;
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

  systemConfigResource = httpResource<any>(() => {
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
  caConnectorResource = httpResource<any>(() => {
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
  systemConfigInit = computed<any>(() => {
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

  loadSmtpIdentifiers(): Observable<PiResponse<any>> {
    return this.http.get<PiResponse<any>>(`${this.systemBaseUrl}names/smtp`, {
      headers: this.authService.getHeaders()
    });
  }

  getDocumentation(): Observable<string> {
    return this.http.get(`${this.systemBaseUrl}documentation`, {
      headers: this.authService.getHeaders(),
      responseType: "text"
    });
  }
}
