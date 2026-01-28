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
import { computed, inject, Injectable, Signal } from "@angular/core";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { lastValueFrom } from "rxjs";

export interface SmsProviderParameter {
  values?: string[];
  required?: boolean;
  type?: string;
  description: string;
}

export interface SmsProvider {
  parameters: Record<string, SmsProviderParameter>;
  options_allowed?: boolean;
  headers_allowed?: boolean;
}

export type SmsProviders = Record<string, SmsProvider>;

export interface SmsGateway {
  id?: number;
  name: string;
  description?: string;
  providermodule: string;
  options: Record<string, string>;
  headers: Record<string, string>;
}

export interface SmsGatewayServiceInterface {
  smsGatewayResource: HttpResourceRef<PiResponse<SmsGateway[]> | undefined>;
  smsProvidersResource: HttpResourceRef<PiResponse<SmsProviders> | undefined>;
  readonly smsGateways: Signal<SmsGateway[]>;
  postSmsGateway(gateway: any): Promise<void>;
  deleteSmsGateway(name: string): Promise<void>;
}

@Injectable({
  providedIn: "root"
})
export class SmsGatewayService implements SmsGatewayServiceInterface {
  private readonly baseUrl = environment.proxyUrl + "/smsgateway/";
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);

  readonly smsGatewayResource = httpResource<PiResponse<SmsGateway[]>>(() => ({
    url: this.baseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  readonly smsProvidersResource = httpResource<PiResponse<SmsProviders>>(() => ({
    url: this.baseUrl + "providers",
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  readonly smsGateways = computed<SmsGateway[]>(() => {
    return this.smsGatewayResource.value()?.result?.value ?? [];
  });

  async postSmsGateway(gateway: any): Promise<void> {
    const request = this.http.post<PiResponse<any>>(this.baseUrl, gateway, { headers: this.authService.getHeaders() });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully saved SMS gateway.`);
        this.smsGatewayResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to save SMS gateway. ` + message);
        throw new Error("post-failed");
      });
  }

  async deleteSmsGateway(name: string): Promise<void> {
    const request = this.http.delete<PiResponse<any>>(`${this.baseUrl}${name}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar($localize`Successfully deleted SMS gateway: ${name}.`);
        this.smsGatewayResource.reload();
      })
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to delete SMS gateway. ` + message);
        throw new Error("delete-failed");
      });
  }
}
