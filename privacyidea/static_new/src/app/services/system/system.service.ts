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
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable } from "@angular/core";

import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";

export type PiNode = {
  name: string;
  uuid: string;
};

export interface SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
  nodesResource: HttpResourceRef<PiResponse<PiNode[], unknown> | undefined>;
  nodes: () => PiNode[];
}

@Injectable({
  providedIn: "root"
})
export class SystemService implements SystemServiceInterface {
  private readonly systemBaseUrl = environment.proxyUrl + "/system/";

  private readonly authService: AuthServiceInterface = inject(AuthService);
  systemConfigResource = httpResource<any>(() => ({
    url: this.systemBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  nodesResource = httpResource<PiResponse<PiNode[]>>({
    url: this.systemBaseUrl + "nodes",
    method: "GET",
    headers: this.authService.getHeaders()
  });

  nodes = computed<PiNode[]>(() => {
    return this.nodesResource.value()?.result?.value ?? [];
  });
}
