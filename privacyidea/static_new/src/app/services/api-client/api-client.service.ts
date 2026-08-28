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
import { inject, Injectable, linkedSignal, signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { lastValueFrom } from "rxjs";

export type ApiClientStatus = "active" | "suspended";

export interface ApiClient {
  id: string;
  display_name: string;
  client_type: string;
  key_id: string;
  status: ApiClientStatus;
  created_at: string;
  last_used_at: string | null;
}

export interface RememberedDevice {
  device_id: string;
  resolver: string;
  user_id: string;
  realm: string;
  user: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
}

export interface IssuedApiKey {
  displayName: string;
  apiKey: string;
}

export interface RememberedDevicesPage {
  devices: RememberedDevice[];
  count: number;
  prev: number | null;
  next: number | null;
}

export interface ApiClientServiceInterface {
  apiClientResource: HttpResourceRef<PiResponse<ApiClient[]> | undefined>;
  apiClients: WritableSignal<ApiClient[]>;
  lastIssuedKey: WritableSignal<IssuedApiKey | null>;

  dismissIssuedKey(): void;

  createClient(displayName: string, clientType: string): Promise<void>;

  updateClient(id: string, patch: { display_name?: string; status?: ApiClientStatus }): Promise<void>;

  rotateClient(id: string, displayName: string): Promise<void>;

  deleteClient(id: string): Promise<void>;

  getRememberedDevices(
    clientId: string,
    options?: { page?: number; pageSize?: number; realm?: string }
  ): Promise<RememberedDevicesPage>;

  revokeDevice(clientId: string, deviceId: string): Promise<void>;

  revokeAllForClient(clientId: string, options?: { realm?: string; user?: string }): Promise<number>;

  revokeAllInRealmAcrossClients(realm: string, user?: string): Promise<number>;
}

@Injectable()
export class ApiClientService implements ApiClientServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  private readonly clientsBaseUrl = environment.proxyUrl + "/clients/";

  apiClientResource = httpResource<PiResponse<ApiClient[]>>(() => {
    if (this.authService.isSelfServiceUser()) return undefined;
    if (!this.contentService.onApiClients()) return undefined;
    return {
      url: this.clientsBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  apiClients: WritableSignal<ApiClient[]> = linkedSignal({
    source: () => ({
      value: this.apiClientResource.hasValue() ? this.apiClientResource.value() : undefined,
      isLoading: this.apiClientResource.isLoading(),
      error: this.apiClientResource.error()
    }),
    computation: (source, previous) => {
      if (source.error) return [];
      const value = source.value?.result?.value;
      if (!value) return source.isLoading ? (previous?.value ?? []) : [];
      return value;
    }
  });

  lastIssuedKey: WritableSignal<IssuedApiKey | null> = signal(null);

  dismissIssuedKey(): void {
    this.lastIssuedKey.set(null);
  }

  async createClient(displayName: string, clientType: string): Promise<void> {
    const request = this.http.post<PiResponse<ApiClient & { api_key: string }>>(
      this.clientsBaseUrl,
      { display_name: displayName, client_type: clientType },
      { headers: this.authService.getHeaders() }
    );
    return lastValueFrom(request)
      .then((response) => {
        const value = response.result?.value;
        if (value) {
          this.lastIssuedKey.set({ displayName: value.display_name, apiKey: value.api_key });
        }
        this.notificationService.success($localize`Successfully created API client: ${displayName}.`);
        this.apiClientResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to create API client. ` + message);
        throw new Error("create-failed");
      });
  }

  async updateClient(id: string, patch: { display_name?: string; status?: ApiClientStatus }): Promise<void> {
    const request = this.http.patch<PiResponse<ApiClient>>(`${this.clientsBaseUrl}${encodeURIComponent(id)}`, patch, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.success($localize`Successfully saved API client.`);
        this.apiClientResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to save API client. ` + message);
        throw new Error("update-failed");
      });
  }

  async rotateClient(id: string, displayName: string): Promise<void> {
    const request = this.http.post<PiResponse<ApiClient & { api_key: string }>>(
      `${this.clientsBaseUrl}${encodeURIComponent(id)}/rotate`,
      {},
      { headers: this.authService.getHeaders() }
    );
    return lastValueFrom(request)
      .then((response) => {
        const value = response.result?.value;
        if (value) {
          this.lastIssuedKey.set({ displayName: value.display_name, apiKey: value.api_key });
        }
        this.notificationService.success($localize`Successfully rotated the API key for: ${displayName}.`);
        this.apiClientResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to rotate API key. ` + message);
        throw new Error("rotate-failed");
      });
  }

  async deleteClient(id: string): Promise<void> {
    const request = this.http.delete<PiResponse<string>>(`${this.clientsBaseUrl}${encodeURIComponent(id)}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.success($localize`Successfully deleted API client.`);
        this.apiClientResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to delete API client. ` + message);
        throw new Error("delete-failed");
      });
  }

  async getRememberedDevices(
    clientId: string,
    options?: { page?: number; pageSize?: number; realm?: string }
  ): Promise<RememberedDevicesPage> {
    let params = new HttpParams().set("page", options?.page ?? 1).set("pagesize", options?.pageSize ?? 50);
    if (options?.realm) params = params.set("realm", options.realm);
    const request = this.http.get<PiResponse<RememberedDevicesPage>>(
      `${this.clientsBaseUrl}${encodeURIComponent(clientId)}/remembered_devices`,
      { headers: this.authService.getHeaders(), params }
    );
    return lastValueFrom(request)
      .then((response) => response.result?.value ?? { devices: [], count: 0, prev: null, next: null })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to load remembered devices. ` + message);
        return { devices: [], count: 0, prev: null, next: null };
      });
  }

  async revokeDevice(clientId: string, deviceId: string): Promise<void> {
    const request = this.http.delete<PiResponse<string>>(
      `${this.clientsBaseUrl}${encodeURIComponent(clientId)}/remembered_devices/${encodeURIComponent(deviceId)}`,
      { headers: this.authService.getHeaders() }
    );
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.success($localize`Successfully revoked the remembered device.`);
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to revoke the remembered device. ` + message);
        throw new Error("revoke-failed");
      });
  }

  async revokeAllForClient(clientId: string, options?: { realm?: string; user?: string }): Promise<number> {
    let params = new HttpParams();
    if (options?.realm) params = params.set("realm", options.realm);
    if (options?.user) params = params.set("user", options.user);
    const request = this.http.delete<PiResponse<number>>(
      `${this.clientsBaseUrl}${encodeURIComponent(clientId)}/remembered_devices`,
      { headers: this.authService.getHeaders(), params }
    );
    return lastValueFrom(request)
      .then((response) => {
        const count = response.result?.value ?? 0;
        this.notificationService.success($localize`Revoked ${count} remembered device(s).`);
        return count;
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to revoke remembered devices. ` + message);
        throw new Error("revoke-all-failed");
      });
  }

  async revokeAllInRealmAcrossClients(realm: string, user?: string): Promise<number> {
    let params = new HttpParams().set("realm", realm);
    if (user) params = params.set("user", user);
    const request = this.http.delete<PiResponse<number>>(`${environment.proxyUrl}/clients/remembered_devices`, {
      headers: this.authService.getHeaders(),
      params
    });
    return lastValueFrom(request)
      .then((response) => {
        const count = response.result?.value ?? 0;
        this.notificationService.success($localize`Revoked ${count} remembered device(s) in realm ${realm}.`);
        return count;
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.error($localize`Failed to revoke remembered devices. ` + message);
        throw new Error("revoke-realm-failed");
      });
  }
}
