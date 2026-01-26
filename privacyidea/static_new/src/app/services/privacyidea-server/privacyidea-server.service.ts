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
import { computed, inject, Injectable, Signal } from "@angular/core";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";

import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { lastValueFrom } from "rxjs";

export interface PrivacyideaServer {
  identifier: string;
  id: string; // compatibility
  url: string;
  tls: boolean;
  description?: string;
  username?: string;
  password?: string;
}

// compatibility alias
export type RemoteServer = PrivacyideaServer;

export type PrivacyideaServers = {
  [key: string]: PrivacyideaServer;
};

export interface PrivacyideaServerServiceInterface {
  privacyideaServerResource: HttpResourceRef<PiResponse<PrivacyideaServers> | undefined>;
  readonly privacyideaServers: Signal<PrivacyideaServer[]>;
  // compatibility
  remoteServerResource: HttpResourceRef<PiResponse<PrivacyideaServers> | undefined>;
  readonly remoteServerOptions: Signal<PrivacyideaServer[]>;

  postPrivacyideaServer(server: PrivacyideaServer): Promise<void>;
  deletePrivacyideaServer(identifier: string): Promise<void>;
  testPrivacyideaServer(params: any): Promise<boolean>;
}

@Injectable({
  providedIn: "root"
})
export class PrivacyideaServerService implements PrivacyideaServerServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);

  readonly privacyideaServerBaseUrl = environment.proxyUrl + "/privacyideaserver/";

  privacyideaServerResource = httpResource<PiResponse<PrivacyideaServers>>(() => ({
    url: this.privacyideaServerBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  // compatibility
  get remoteServerResource() { return this.privacyideaServerResource; }

  privacyideaServers = computed<PrivacyideaServer[]>(() => {
    const res = this.privacyideaServerResource.value();
    const values = res?.result?.value;
    if (values) {
      return Object.entries(values).map(([identifier, server]) => ({
        ...server,
        identifier,
        id: identifier // compatibility
      }));
    }
    return [];
  });

  // compatibility
  get remoteServerOptions() { return this.privacyideaServers; }

  async postPrivacyideaServer(server: PrivacyideaServer): Promise<void> {
    const url = `${this.privacyideaServerBaseUrl}${server.identifier}`;
    const request = this.http.post<PiResponse<any>>(url, server, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved privacyIDEA server.`);
        this.privacyideaServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save privacyIDEA server. ` + message);
        throw new Error("post-failed");
      });
  }

  async deletePrivacyideaServer(identifier: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.privacyideaServerBaseUrl}${identifier}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted privacyIDEA server: ${identifier}.`);
        this.privacyideaServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete privacyIDEA server. ` + message);
        throw new Error("delete-failed");
      });
  }

  async testPrivacyideaServer(params: any): Promise<boolean> {
    const url = `${this.privacyideaServerBaseUrl}test_request`;
    const request = this.http.post<PiResponse<boolean>>(url, params, { headers: this.authService.getHeaders() });
    return lastValueFrom(request)
      .then((res) => {
        if (res?.result?.value) {
          this.notificationService.openSnackBar($localize`Test request successful.`);
          return true;
        }
        this.notificationService.openSnackBar($localize`Test request failed.`);
        return false;
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to send test request. ` + message);
        return false;
      });
  }
}
