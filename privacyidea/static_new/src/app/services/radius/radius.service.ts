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
import { computed, inject, Injectable, Signal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { PiResponse } from "../../app.component";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
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

export type RadiusServers = {
  [key: string]: RadiusServer;
};

export interface RadiusServiceInterface {
  radiusServerResource: HttpResourceRef<PiResponse<RadiusServers> | undefined>;
  readonly radiusServers: Signal<RadiusServer[]>;
  postRadiusServer(server: RadiusServer): Promise<void>;
  testRadiusServer(params: any): Promise<boolean>;
  deleteRadiusServer(identifier: string): Promise<void>;
}

@Injectable({
  providedIn: "root"
})
export class RadiusService implements RadiusServiceInterface {
  readonly radiusServerBaseUrl = environment.proxyUrl + "/radiusserver/";

  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly http: HttpClient = inject(HttpClient);

  readonly radiusServerResource = httpResource<PiResponse<RadiusServers>>(() => {
    return {
      url: `${this.radiusServerBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly radiusServers = computed<RadiusServer[]>(() => {
    const res = this.radiusServerResource.value();
    const values = res?.result?.value;
    if (values) {
      return Object.entries(values).map(([identifier, server]) => ({
        ...server,
        identifier
      }));
    }
    return [];
  });

  async postRadiusServer(server: RadiusServer): Promise<void> {
    const url = `${this.radiusServerBaseUrl}${server.identifier}`;
    const request = this.http.post<PiResponse<any>>(url, server, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved RADIUS server.`);
        this.radiusServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save RADIUS server. ` + message);
        throw new Error("post-failed");
      });
  }

  async testRadiusServer(params: any): Promise<boolean> {
    const url = `${this.radiusServerBaseUrl}test_request`;
    const request = this.http.post<PiResponse<boolean>>(url, params, { headers: this.authService.getHeaders() });
    return lastValueFrom(request)
      .then((res) => {
        if (res?.result?.value) {
          this.notificationService.openSnackBar($localize`RADIUS request successful.`);
          return true;
        } else {
          this.notificationService.openSnackBar($localize`RADIUS request failed!`);
          return false;
        }
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to send RADIUS test request. ` + message);
        return false;
      });
  }

  async deleteRadiusServer(identifier: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.radiusServerBaseUrl}${identifier}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted RADIUS server: ${identifier}.`);
        this.radiusServerResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete RADIUS server. ` + message);
        throw new Error("delete-failed");
      });
  }
}
