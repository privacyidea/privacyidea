/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { lastValueFrom } from "rxjs";

export type RadiusServerConfigurations = {
  [key: string]: any;
};

export interface RadiusServerConfiguration {
  name: string;
  description: string;
  dictionary: string;
  port: number;
  retries: number;
  server: string;
  timeout: number;
}

export interface RadiusServerServiceInterface {
  radiusServerConfigurationResource: HttpResourceRef<PiResponse<RadiusServerConfigurations> | undefined>;
  radiusServerConfigurations: WritableSignal<RadiusServerConfiguration[]>;
  postRadiusServer(server: any): Promise<void>;
  deleteRadiusServer(name: string): Promise<void>;
}

@Injectable({
  providedIn: "root"
})
export class RadiusServerService implements RadiusServerServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);

  readonly radiusServerBaseUrl = environment.proxyUrl + "/radiusserver/";

  radiusServerConfigurationResource = httpResource<PiResponse<RadiusServerConfigurations>>(() => ({
    url: this.radiusServerBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  radiusServerConfigurations: WritableSignal<RadiusServerConfiguration[]> = linkedSignal({
    source: this.radiusServerConfigurationResource.value,
    computation: (source, previous) =>
      Object.entries(source?.result?.value ?? {}).map(([name, properties]) => ({ name, ...properties })) ??
      previous?.value ??
      []
  });

  async postRadiusServer(server: any): Promise<void> {
    const url = `${this.radiusServerBaseUrl}${server.identifier || server.name}`;
    const request = this.http.post<PiResponse<any>>(url, server, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved RADIUS server.`);
        this.radiusServerConfigurationResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save RADIUS server. ` + message);
        throw new Error("post-failed");
      });
  }

  async deleteRadiusServer(name: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.radiusServerBaseUrl}${name}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted RADIUS server: ${name}.`);
        this.radiusServerConfigurationResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete RADIUS server. ` + message);
        throw new Error("delete-failed");
      });
  }
}
