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
import { HttpErrorResponse, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";

export type Realms = Map<string, Realm>;

export interface Realm {
  default: boolean;
  id: number;
  option: string;
  resolver: RealmResolvers;
}

export type RealmResolvers = Array<RealmResolver>;

export interface RealmResolver {
  name: string;
  node: string;
  type: string;
  priority: any;
}

export interface RealmServiceInterface {
  selectedRealms: WritableSignal<string[]>;
  realmResource: HttpResourceRef<PiResponse<Realms> | undefined>;
  realmOptions: Signal<string[]>;
  defaultRealmResource: HttpResourceRef<PiResponse<Realms> | undefined>;
  defaultRealm: Signal<string>;
}

@Injectable({
  providedIn: "root"
})
export class RealmService implements RealmServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  selectedRealms = signal<string[]>([]);

  realmResource = httpResource<PiResponse<Realms>>(() => {
    if (
      this.authService.role() === "user" ||
      (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS) &&
        !this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS) &&
        ![
          ROUTE_PATHS.TOKENS,
          ROUTE_PATHS.USERS,
          ROUTE_PATHS.TOKENS_CONTAINERS_CREATE,
          ROUTE_PATHS.TOKENS_ENROLLMENT
        ].includes(this.contentService.routeUrl()))
    ) {
      return undefined;
    }
    return {
      url: environment.proxyUrl + "/realm/",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  realmOptions = computed(() => {
    const realms = this.realmResource.value()?.result?.value;
    return realms ? Object.keys(realms) : [];
  });

  defaultRealmResource = httpResource<PiResponse<Realms>>(() => {
    if (
      this.authService.role() === "user" ||
      (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS) &&
        !this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS) &&
        ![
          ROUTE_PATHS.TOKENS,
          ROUTE_PATHS.USERS,
          ROUTE_PATHS.TOKENS_CONTAINERS_CREATE,
          ROUTE_PATHS.TOKENS_ENROLLMENT
        ].includes(this.contentService.routeUrl()))
    ) {
      return undefined;
    }
    return {
      url: environment.proxyUrl + "/defaultrealm",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  defaultRealm = computed<string>(() => {
    const data = this.defaultRealmResource.value();
    if (data?.result?.value) {
      return Object.keys(data.result?.value)[0] ?? "";
    }
    return "";
  });

  constructor() {
    effect(() => {
      if (this.realmResource.error()) {
        const realmError = this.realmResource.error() as HttpErrorResponse;
        console.error("Failed to get realms.", realmError.message);
        const message = realmError.error?.result?.error?.message || realmError.message;
        this.notificationService.openSnackBar("Failed to get realms. " + message);
      }
    });

    effect(() => {
      if (this.defaultRealmResource.error()) {
        const defaultRealmError = this.defaultRealmResource.error() as HttpErrorResponse;
        console.error("Failed to get default realm.", defaultRealmError.message);
        const message = defaultRealmError.error?.result?.error?.message || defaultRealmError.message;
        this.notificationService.openSnackBar("Failed to get default realm. " + message);
      }
    });
  }
}
