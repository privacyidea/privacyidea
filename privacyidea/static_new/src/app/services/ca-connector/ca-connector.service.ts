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
import { inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { lastValueFrom } from "rxjs";

export interface CaConnector {
  connectorname: string;
  type: string;
  data: Record<string, any>;
  templates?: Record<string, any>;
}

export type CaConnectors = CaConnector[];

export interface CaConnectorServiceInterface {
  caConnectorServiceResource: HttpResourceRef<PiResponse<CaConnectors> | undefined>;
  caConnectors: WritableSignal<CaConnectors>;

  postCaConnector(connector: CaConnector): Promise<void>;
  deleteCaConnector(connectorname: string): Promise<void>;
  getCaSpecificOptions(catype: string, params: any): Promise<any>;
}

@Injectable({
  providedIn: "root"
})
export class CaConnectorService implements CaConnectorServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);

  readonly caConnectorBaseUrl = environment.proxyUrl + "/caconnector/";

  caConnectorServiceResource = httpResource<PiResponse<CaConnectors>>(() => ({
    url: this.caConnectorBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  caConnectors: WritableSignal<CaConnectors> = linkedSignal({
    source: this.caConnectorServiceResource.value,
    computation: (source, previous) => source?.result?.value ?? previous?.value ?? []
  });

  async postCaConnector(connector: CaConnector): Promise<void> {
    const url = `${this.caConnectorBaseUrl}${connector.connectorname}`;
    const request = this.http.post<PiResponse<any>>(url, connector.data, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved CA connector.`);
        this.caConnectorServiceResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save CA connector. ` + message);
        throw new Error("post-failed");
      });
  }

  async deleteCaConnector(connectorname: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.caConnectorBaseUrl}${connectorname}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted CA connector: ${connectorname}.`);
        this.caConnectorServiceResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete CA connector. ` + message);
        throw new Error("delete-failed");
      });
  }

  async getCaSpecificOptions(catype: string, params: any): Promise<any> {
    const pstring = new URLSearchParams(params).toString();
    const url = `${this.caConnectorBaseUrl}specific/${catype}?${pstring}`;
    const request = this.http.get<PiResponse<any>>(url, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then((res) => {
        return res?.result?.value;
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to fetch CA specific options. ` + message);
        throw new Error("fetch-failed");
      });
  }
}
