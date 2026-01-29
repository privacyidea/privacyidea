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


import { inject, Injectable } from "@angular/core";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { HttpClient, httpResource } from "@angular/common/http";
import { PiResponse } from "../../app.component";
import { environment } from "../../../environments/environment";

export type Subscription = {
  active_tokens: number,
  active_users: number,
  application: string,
  by_address: string,
  by_email: string,
  by_name: string,
  by_phone: string,
  by_url: string,
  date_from: string,
  date_till: string,
  for_address: string,
  for_comment: string,
  for_email: string,
  for_name: string,
  for_phone: string,
  for_url: string,
  id: number,
  level: string,
  num_clients: number,
  num_tokens: number,
  num_users: number,
  signature: string,
  timedelta: number
};

@Injectable({
  providedIn: "root"
})
export class SubscriptionService {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);

  subscriptionResource = httpResource<PiResponse<Subscription[]>>(() => {
    if (this.authService.actionAllowed("managesubscription")) {
      return undefined;
    }
    // Only load the default realm on relevant routes.
    if (!this.contentService.onSubscription()) {
      return undefined;
    }

    return {
      url: environment.proxyUrl + "/subscriptions/",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

}