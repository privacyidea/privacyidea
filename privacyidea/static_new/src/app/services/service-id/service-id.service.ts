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

type ServiceIds = {
  [key: string]: _ServiceId;
};

interface _ServiceId {
  description: string;
  id: number;
}

export interface ServiceId {
  servicename: string;
  description: string;
  id?: number;
}

export interface ServiceIdServiceInterface {
  serviceIdResource: HttpResourceRef<PiResponse<ServiceIds> | undefined>;
  serviceIds: WritableSignal<ServiceId[]>;
  postServiceId(serviceId: ServiceId): Promise<void>;
  deleteServiceId(servicename: string): Promise<void>;
}

@Injectable({
  providedIn: "root"
})
export class ServiceIdService implements ServiceIdServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);

  private readonly serviceIdBaseUrl = environment.proxyUrl + "/serviceid/";

  serviceIdResource = httpResource<PiResponse<ServiceIds>>(() => ({
    url: this.serviceIdBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  serviceIds: WritableSignal<ServiceId[]> = linkedSignal({
    source: this.serviceIdResource.value,
    computation: (source, previous) => {
      const value = source?.result?.value;
      if (!value) {
        return previous?.value ?? [];
      }
      return Object.entries(value).map(([servicename, { description, id }]) => ({
        servicename,
        description,
        id
      }));
    }
  });

  async postServiceId(serviceId: ServiceId): Promise<void> {
    const url = `${this.serviceIdBaseUrl}${serviceId.servicename}`;
    const request = this.http.post<PiResponse<any>>(url, serviceId, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved service ID.`);
        this.serviceIdResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save service ID. ` + message);
        throw new Error("post-failed");
      });
  }

  async deleteServiceId(servicename: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.serviceIdBaseUrl}${servicename}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted service ID: ${servicename}.`);
        this.serviceIdResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete service ID. ` + message);
        throw new Error("delete-failed");
      });
  }
}
