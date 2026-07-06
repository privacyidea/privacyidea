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
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { lastValueFrom } from "rxjs";

export type CaConnectorConfigValue = string | number | boolean | string[] | null;
export type CaConnectorData = Record<string, CaConnectorConfigValue>;
export type CaConnectorTemplate = Record<string, CaConnectorConfigValue>;
export type CaConnectorTemplates = Record<string, CaConnectorTemplate>;

export interface CaConnector {
  connectorname: string;
  type: string;
  data: CaConnectorData;
  templates?: CaConnectorTemplates;
}

export type CaConnectors = CaConnector[];

export type CaSpecificOptions = Record<string, CaConnectorConfigValue | CaConnectorTemplates>;

export interface CaSpecificOptionsParams {
  hostname: string;
  port?: string | number;
  use_ssl?: boolean | string;
  ssl_ca_cert?: string;
  ssl_client_cert?: string;
  ssl_client_key?: string;
  ssl_client_key_password?: string;
  http_proxy?: string;
}

export interface CaConnectorServiceInterface {
  caConnectorResource: HttpResourceRef<PiResponse<CaConnectors> | undefined>;
  caConnectors: WritableSignal<CaConnectors>;

  postCaConnector(connector: CaConnector): Promise<void>;

  deleteCaConnector(connectorname: string): Promise<void>;

  getCaSpecificOptions(catype: string, params: CaSpecificOptionsParams): Promise<CaSpecificOptions | undefined>;
}

@Injectable()
export class CaConnectorService implements CaConnectorServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  readonly caConnectorBaseUrl = environment.proxyUrl + "/caconnector/";

  caConnectorResource = httpResource<PiResponse<CaConnectors>>(() => {
    if (!this.contentService.onExternalCaConnectors()) {
      return undefined;
    }
    return {
      url: this.caConnectorBaseUrl,
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
      const value = source.value?.result?.value;
      if (!value) return source.isLoading ? (previous?.value ?? []) : [];
      return value;
    }
  });

  async postCaConnector(connector: CaConnector): Promise<void> {
    const url = `${this.caConnectorBaseUrl}${encodeURIComponent(connector.connectorname)}`;
    const request = this.http.post<PiResponse<number>>(url, connector.data, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.success($localize`Successfully saved CA connector.`);
        this.caConnectorResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to save CA connector. ` + message);
        throw new Error("post-failed");
      });
  }

  async deleteCaConnector(connectorname: string): Promise<void> {
    const request = this.http.delete<PiResponse<number>>(
      `${this.caConnectorBaseUrl}${encodeURIComponent(connectorname)}`,
      {
        headers: this.authService.getHeaders()
      }
    );
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.success($localize`Successfully deleted CA connector: ${connectorname}.`);
        this.caConnectorResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to delete CA connector. ` + message);
        throw new Error("delete-failed");
      });
  }

  async getCaSpecificOptions(catype: string, params: CaSpecificOptionsParams): Promise<CaSpecificOptions | undefined> {
    const pstring = new URLSearchParams(params as unknown as Record<string, string>).toString();
    const url = `${this.caConnectorBaseUrl}specific/${encodeURIComponent(catype)}?${pstring}`;
    const request = this.http.get<PiResponse<CaSpecificOptions>>(url, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then((res) => {
        return res?.result?.value;
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to fetch CA specific options. ` + message);
        throw new Error("fetch-failed");
      });
  }
}
