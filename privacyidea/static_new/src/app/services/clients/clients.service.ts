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
import { httpResource, HttpResourceRef } from "@angular/common/http";
import { effect, inject, Injectable, signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";

export interface ClientData {
  hostname?: string | null;
  ip?: string | null;
  lastseen?: string | null;
  application?: string | null;
}

export type ClientsDict = Record<string, ClientData[]>;

export interface ClientsServiceInterface {
  clientsResource: HttpResourceRef<PiResponse<ClientsDict> | undefined>;

  requestClientsForAutocomplete(): void;
}

@Injectable()
export class ClientsService implements ClientsServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService = inject(NotificationService);

  private clientsBaseUrl = environment.proxyUrl + "/client/";

  private autocompleteRequested = signal(false);
  clientsResource = httpResource<PiResponse<ClientsDict>>(() => {
    if (!this.authService.actionAllowed("clienttype")) {
      return undefined;
    }
    if (!this.autocompleteRequested() && this.contentService.routeUrl() !== ROUTE_PATHS.CLIENTS) {
      return undefined;
    }
    return {
      url: this.clientsBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {}
    };
  });

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.clientsResource.error(), "clients");
    });
  }

  requestClientsForAutocomplete(): void {
    if (!this.autocompleteRequested()) {
      this.autocompleteRequested.set(true);
    }
  }


}
