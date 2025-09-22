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
import { AuthService, AuthServiceInterface } from "../auth/auth.service";

import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";

export type RemoteServerOptions = RemoteServer[];

export interface RemoteServer {
  url: string;
  id: string;
  name: string;
}

export interface PrivacyideaServerServiceInterface {
  remoteServerResource: HttpResourceRef<PiResponse<RemoteServerOptions> | undefined>;
  remoteServerOptions: WritableSignal<RemoteServerOptions>;
}

@Injectable({
  providedIn: "root"
})
export class PrivacyideaServerService implements PrivacyideaServerServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  remoteServerResource = httpResource<PiResponse<RemoteServerOptions>>(() => ({
    url: environment.proxyUrl + "/privacyideaserver/",
    method: "GET",
    headers: this.authService.getHeaders()
  }));
  remoteServerOptions: WritableSignal<RemoteServerOptions> = linkedSignal({
    source: this.remoteServerResource.value,
    computation: (source, previous) => {
      let servers = previous?.value ?? [];
      if (source?.result?.value) {
        let response = source.result.value;
        servers = Object.entries(response).map(([server, options]) => {
          return {
            name: server,
            url: options.url,
            id: options.id
          };
        });
      }
      return servers;
    }
  });
}
