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
import { computed, effect, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { Observable, catchError, throwError } from "rxjs";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";

export type AdminRealms = string[];
export type Realms = { [key: string]: Realm };

export interface Realm {
  default: boolean;
  id: number;
  option: string;
  resolver: RealmResolvers;
}

export interface ResolverDisplay {
  name: string;
  type: string;
  priority: number | null;
}

export interface ResolverGroup {
  nodeId: string;
  nodeLabel: string;
  resolvers: ResolverDisplay[];
}

export interface RealmRow {
  name: string;
  isDefault: boolean;
  resolverGroups: ResolverGroup[];
  resolversText: string;
}

export type RealmResolvers = Array<RealmResolver>;

export interface RealmResolver {
  name: string;
  node: string;
  type: string;
  priority: number | null;
}

export interface RealmServiceInterface {
  selectedRealms: WritableSignal<string[]>;
  realmResource: HttpResourceRef<PiResponse<Realms> | undefined>;
  realms: Signal<Realms>;
  realmOptions: Signal<string[]>;
  adminRealmResource: HttpResourceRef<PiResponse<AdminRealms> | undefined>;
  adminRealmOptions: Signal<string[]>;
  defaultRealmResource: HttpResourceRef<PiResponse<Realms> | undefined>;
  defaultRealm: Signal<string>;

  createRealm(
    realm: string,
    nodeId: string,
    resolvers: { name: string; priority?: number | null }[]
  ): Observable<PiResponse<any>>;

  deleteRealm(realm: string): Observable<PiResponse<number | any>>;

  setDefaultRealm(realm: string): Observable<PiResponse<number | any>>;
}

@Injectable({
  providedIn: "root"
})
export class RealmService implements RealmServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http: HttpClient = inject(HttpClient);
  private onAllowedRoute = computed(() => {
    return (
      this.contentService.onTokenDetails() ||
      this.contentService.onTokensContainersDetails() ||
      this.contentService.onTokens() ||
      this.contentService.onUsers() ||
      this.contentService.onTokensContainersCreate() ||
      this.contentService.onTokensEnrollment() ||
      this.contentService.onTokensImport() ||
      this.contentService.onPolicies() ||
      this.contentService.onUserRealms() ||
      this.contentService.onTokensContainersTemplates()
    );
  });

  selectedRealms = signal<string[]>([]);

  realmResource = httpResource<PiResponse<Realms>>(() => {
    // Do not load the default realm for non-admin users.
    if (this.authService.role() === "user") {
      return undefined;
    }
    // Only load the default realm on relevant routes.
    if (!this.onAllowedRoute()) {
      return undefined;
    }

    return {
      url: environment.proxyUrl + "/realm/",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  realms = computed(() => {
    if (!this.realmResource.hasValue()) return {};
    const data = this.realmResource.value();
    return data?.result?.value || {};
  });

  realmOptions = computed(() => {
    const realms = this.realms();
    return realms ? Object.keys(realms) : [];
  });

  // adminRealmResource: HttpResourceRef<PiResponse<Realms, unknown> | undefined>;
  adminRealmResource = httpResource<PiResponse<AdminRealms>>(() => {
    // Do not load the default realm for non-admin users.
    if (this.authService.role() === "user") {
      return undefined;
    }
    // Only load the default realm on relevant routes.
    if (!this.onAllowedRoute()) {
      return undefined;
    }

    return {
      url: environment.proxyUrl + "/realm/superuser",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  adminRealmOptions: Signal<string[]> = computed(() => {
    if (!this.adminRealmResource.hasValue()) return [];
    const realms = this.adminRealmResource.value()?.result?.value;
    return realms ? realms : [];
  });

  defaultRealmResource = httpResource<PiResponse<Realms>>(() => {
    // Do not load the default realm for non-admin users.
    if (this.authService.role() === "user") {
      return undefined;
    }
    // Only load the default realm on relevant routes.
    if (!this.onAllowedRoute()) {
      return undefined;
    }

    return {
      url: environment.proxyUrl + "/defaultrealm",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  defaultRealm = computed<string>(() => {
    let defaultRealm = "";
    if (this.defaultRealmResource.hasValue()) {
      const data = this.defaultRealmResource.value();
      if (data?.result?.value) {
        defaultRealm = Object.keys(data.result?.value)[0] ?? "";
      }
    }
    return defaultRealm;
  });

  createRealm(
    realm: string,
    nodeId: string,
    resolvers: { name: string; priority?: number | null }[]
  ): Observable<PiResponse<any>> {
    let url: string;
    let body: any;

    if (!nodeId) {
      url = `${environment.proxyUrl}/realm/${encodeURIComponent(realm)}`;

      const resolverNames = resolvers.map((r) => r.name);
      body = {
        resolvers: resolverNames
      };

      resolvers.forEach((r) => {
        const num = Number(r.priority);
        if (r.priority !== null && r.priority !== undefined && !Number.isNaN(num)) {
          body[`priority.${r.name}`] = num;
        }
      });
    } else {
      url = `${environment.proxyUrl}/realm/${encodeURIComponent(realm)}/node/${nodeId}`;
      body = {
        resolver: resolvers.map((r) => {
          const base: any = { name: r.name };
          const num = Number(r.priority);
          if (r.priority !== null && r.priority !== undefined && !Number.isNaN(num)) {
            base.priority = num;
          }
          return base;
        })
      };
    }

    return this.http.post<PiResponse<any>>(url, body, {
      headers: this.authService.getHeaders()
    }).pipe(
      catchError((error) => {
        console.error("Failed to create realm.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to create realm. " + message);
        return throwError(() => error);
      })
    );
  }

  deleteRealm(realm: string): Observable<PiResponse<number | any>> {
    const encodedRealm = encodeURIComponent(realm);
    const url = `${environment.proxyUrl}/realm/${encodedRealm}`;

    return this.http.delete<PiResponse<number | any>>(url, {
      headers: this.authService.getHeaders()
    }).pipe(
      catchError((error) => {
        console.error("Failed to delete realm.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete realm. " + message);
        return throwError(() => error);
      })
    );
  }

  setDefaultRealm(realm: string): Observable<PiResponse<number | any>> {
    const encodedRealm = encodeURIComponent(realm);
    const url = `${environment.proxyUrl}/defaultrealm/${encodedRealm}`;

    return this.http.post<PiResponse<number | any>>(url, {}, { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error("Failed to set default realm.", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to set default realm. " + message);
        return throwError(() => error);
      })
    );
  }

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.realmResource.error(), "realms");
    });

    effect(() => {
      this.notificationService.handleResourceError(this.defaultRealmResource.error(), "default realm");
    });

    effect(() => {
      this.notificationService.handleResourceError(this.adminRealmResource.error(), "admin realms");
    });
  }
}
