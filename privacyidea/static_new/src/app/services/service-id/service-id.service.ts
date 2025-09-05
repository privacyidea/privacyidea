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
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";

type ServiceIds = {
  [key: string]: _ServiceId;
};

interface _ServiceId {
  description: string;
  id: number;
}

export interface ServiceId {
  name: string;
  description: string;
  id: number;
}

export interface ServiceIdServiceInterface {
  serviceIdResource: HttpResourceRef<PiResponse<ServiceIds> | undefined>;
  serviceIds: WritableSignal<ServiceId[]>;
}

@Injectable({
  providedIn: "root"
})
export class ServiceIdService implements ServiceIdServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  serviceIdResource = httpResource<PiResponse<ServiceIds>>(() => ({
    url: environment.proxyUrl + "/serviceid/",
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
      return Object.entries(value).map(([name, { description, id }]) => ({
        name,
        description,
        id
      }));
    }
  });
}
