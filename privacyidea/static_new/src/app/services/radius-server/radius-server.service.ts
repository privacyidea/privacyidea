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
import { effect, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { lastValueFrom } from "rxjs";

export interface RadiusServer {
  identifier: string;
  server: string;
  port: number;
  timeout: number;
  retries: number;
  secret: string;
  dictionary?: string;
  description?: string;
  options?: {
    message_authenticator?: boolean;
  };
}

export type RadiusServers = Record<string, RadiusServer>;

export interface RadiusServerServiceInterface {
  radiusServerResource: HttpResourceRef<PiResponse<RadiusServers> | undefined>;
  readonly radiusServers: Signal<RadiusServer[]>;

  postRadiusServer(server: RadiusServer): Promise<void>;

  testRadiusServer(params: RadiusServer): Promise<boolean>;

  deleteRadiusServer(identifier: string): Promise<void>;
}

@Injectable()
export class RadiusServerService implements RadiusServerServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  readonly radiusServerBaseUrl = environment.proxyUrl + "/radiusserver/";
  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.radiusServerResource.error(), "RADIUS servers");
    });
  }

  radiusServerResource = httpResource<PiResponse<RadiusServers>>(() => {
    if (!this.contentService.onExternalRadius()) {
      return undefined;
    }
    return {
      url: this.radiusServerBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  radiusServers: WritableSignal<RadiusServer[]> = linkedSignal({
    source: () => ({
      value: this.radiusServerResource.hasValue() ? this.radiusServerResource.value() : undefined,
      isLoading: this.radiusServerResource.isLoading(),
      error: this.radiusServerResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return [];
      if (!source.value) return source.isLoading ? (previous?.value ?? []) : [];
      return Object.entries(source.value.result?.value ?? {}).map(([identifier, server]) => ({
        ...server,
        identifier
      }));
    }
  });

  async postRadiusServer(server: RadiusServer): Promise<void> {
    const url = `${this.radiusServerBaseUrl}${encodeURIComponent(server.identifier)}`;
    const request = this.http.post<PiResponse<any>>(url, server, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.success($localize`Successfully saved RADIUS server.`);
        this.radiusServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to save RADIUS server. ` + message);
        throw new Error("post-failed");
      });
  }

  async testRadiusServer(params: RadiusServer): Promise<boolean> {
    const url = `${this.radiusServerBaseUrl}test_request`;
    const request = this.http.post<PiResponse<boolean>>(url, params, { headers: this.authService.getHeaders() });

    try {
      const res = await lastValueFrom(request);

      if (res?.result?.value) {
        this.notificationService.success($localize`RADIUS request successful.`);
        return true;
      }

      this.notificationService.error($localize`RADIUS request failed!`);
      return false;
    } catch (error: any) {
      const message = error.error?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to send RADIUS test request. ` + message);
      return false;
    }
  }
  async deleteRadiusServer(identifier: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.radiusServerBaseUrl}${encodeURIComponent(identifier)}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.success($localize`Successfully deleted RADIUS server: ${identifier}.`);
        this.radiusServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to delete RADIUS server. ` + message);
        throw new Error("delete-failed");
      });
  }
}
