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
import { computed, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";

import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { CaConnectors } from "../ca-connector/ca-connector.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";

export type PiNode = {
  name: string;
  uuid: string;
};

export interface NodeInfo {
  name: string;
  uuid: string;
}

export interface SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
  radiusServerResource: HttpResourceRef<any>;
  caConnectorResource?: HttpResourceRef<any>;
  caConnectors?: WritableSignal<CaConnectors>;
  nodesResource: HttpResourceRef<any>;
  systemConfig: Signal<any>;
  nodes: Signal<PiNode[]>;
}

@Injectable({
  providedIn: "root"
})
export class SystemService implements SystemServiceInterface {
  private readonly systemBaseUrl = environment.proxyUrl + "/system/";

  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);

  systemConfigResource = httpResource<any>(() => {
    // Only load system config on enrollment or wizard routes.
    if (!this.contentService.onTokensEnrollment() ||
      this.contentService.onTokensWizard()) {
      return undefined;
    }

    return {
      url: this.systemBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  radiusServerResource = httpResource<any>(() => {
    // Do not load CA connectors details if the action is not allowed.
    if (!this.authService.actionAllowed("enrollRADIUS")) {
      return undefined;
    }
    // Only load CA connectors on enrollment or token wizard routes.
    if (!this.contentService.onTokensEnrollment() &&
      !this.contentService.onTokensWizard()) {
      return undefined;
    }

    return {
      url: this.systemBaseUrl + "/names/radius",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  caConnectorResource = httpResource<any>(() => {
    // Do not load CA connectors details if the action is not allowed.
    if (!this.authService.actionAllowed("enrollCERTIFICATE")) {
      return undefined;
    }
    // Only load CA connectors on enrollment or token wizard routes.
    if (!this.contentService.onTokensEnrollment() ||
      !this.contentService.onTokensWizard()) {
      return undefined;
    }

    return {
      url: environment.proxyUrl + "/system/names/caconnector",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  caConnectors: WritableSignal<CaConnectors> = linkedSignal({
    source: this.caConnectorResource?.value,
    computation: (source, previous) => source?.result?.value ?? previous?.value ?? []
  });
  nodesResource = httpResource<PiResponse<PiNode[]>>({
    url: this.systemBaseUrl + "nodes",
    method: "GET",
    headers: this.authService.getHeaders()
  });
  systemConfig = computed<any>(() => {
    return this.systemConfigResource.value()?.result?.value ?? {};
  });
  nodes = computed<PiNode[]>(() => {
    return this.nodesResource.value()?.result?.value ?? [];
  });
}
