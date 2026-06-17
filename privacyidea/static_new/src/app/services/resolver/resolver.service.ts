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

import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { parseBooleanValue } from "@utils/parse-boolean-value";
import { catchError, Observable, throwError } from "rxjs";

export type ResolverType =
  | "ldapresolver"
  | "sqlresolver"
  | "passwdresolver"
  | "scimresolver"
  | "httpresolver"
  | "entraidresolver"
  | "keycloakresolver";

export interface LdapPreset {
  name: string;
  loginName: string;
  searchFilter: string;
  userInfo: string;
  uidType: string;
}

export type BindType = "" | "Simple" | "Anonymous" | "SASL Digest-MD5" | "NTLM" | "SASL Kerberos";

export interface ResolverData {
  [key: string]: unknown;
  USERINFO?: string;
  Map?: string;
  attribute_mapping?: Record<string, string>;
  Editable?: boolean | string;
  editable?: boolean | string;
  EDITABLE?: boolean | string;
}

export type Resolvers = Record<string, Resolver>;

export interface Resolver {
  censor_keys: string[];
  data: ResolverData;
  resolvername: string;
  type: ResolverType;
}

export interface LDAPResolverData extends ResolverData {
  LDAPURI: string;
  LDAPBASE: string;
  AUTHTYPE: BindType;
  BINDDN: string;
  BINDPW: string;
  TIMEOUT: number;
  CACHE_TIMEOUT: number;
  SIZELIMIT: number;
  LOGINNAMEATTRIBUTE: string;
  LDAPSEARCHFILTER: string;
  USERINFO: string;
  UIDTYPE: string;
  NOREFERRALS: boolean;
  NOSCHEMAS: boolean;
  EDITABLE: boolean;
  START_TLS: boolean;
  TLS_VERIFY: boolean;
  TLS_VERSION: string;
  SCOPE: string;
  TLS_CA_FILE?: string;
  SERVERPOOL_ROUNDS?: number;
  SERVERPOOL_SKIP?: number;
  SERVERPOOL_PERSISTENT?: boolean;
  OBJECT_CLASSES?: string;
  DN_TEMPLATE?: string;
  MULTIVALUEATTRIBUTES?: string;
  recursive_group_search?: boolean;
  group_base_dn?: string;
  group_search_filter?: string;
  group_name_attribute?: string;
  group_attribute_mapping_key?: string;
}

export interface SQLResolverData extends ResolverData {
  Database: string;
  Driver: string;
  Server: string;
  Port: number;
  User: string;
  Password: string;
  Table: string;
  Limit?: number;
  Map: string;
  Editable: boolean;
  Password_Hash_Type: string;
  poolSize?: number;
  poolTimeout?: number;
  poolRecycle?: number;
  conParams?: string;
  Encoding?: string;
  Where?: string;
}

export interface PasswdResolverData extends ResolverData {
  fileName?: string;
  filename?: string;
}

/**
 * Configuration of a single HTTP request the resolver performs, matching the
 * backend `RequestConfig` (see lib/resolvers/HTTPResolver.py). The mapping and
 * header fields can be sent/received either as objects or as JSON strings.
 */
export interface HTTPRequestConfig {
  method?: string;
  endpoint?: string;
  headers?: Record<string, string> | string;
  requestMapping?: Record<string, unknown> | string;
  responseMapping?: Record<string, unknown> | string;
  hasSpecialErrorHandler?: boolean;
  errorResponse?: Record<string, unknown> | string;
}

/**
 * Like {@link HTTPRequestConfig} but with the extra fields the backend reads
 * for the user-groups endpoint (see lib/resolvers/HTTPResolver.py).
 */
export interface HTTPUserGroupsConfig extends HTTPRequestConfig {
  active?: boolean;
  pi_user_groups_key?: string;
  user_groups_attribute?: string;
}

export interface HTTPResolverData extends ResolverData {
  base_url?: string;
  attribute_mapping?: Record<string, string>;
  Editable?: boolean;
  verify_tls?: boolean;
  tls_ca_path?: string;
  timeout?: number;
  advanced?: boolean;
  config_get_user_list?: HTTPRequestConfig;
  config_get_user_by_id?: HTTPRequestConfig;
  config_get_user_by_name?: HTTPRequestConfig;
  config_create_user?: HTTPRequestConfig;
  config_edit_user?: HTTPRequestConfig;
  config_delete_user?: HTTPRequestConfig;
  config_authorization?: HTTPRequestConfig;
  // The backend also accepts this as a JSON string.
  config_user_auth?: HTTPRequestConfig | string;
  config_get_user_groups?: HTTPUserGroupsConfig;
}

export interface EntraIDResolverData extends HTTPResolverData {
  client_id?: string;
  tenant?: string;
  client_credential_type?: "secret" | "certificate";
  client_secret?: string;
  client_certificate?: {
    private_key_file?: string;
    private_key_password?: string;
    certificate_fingerprint?: string;
  };
  authority?: string;
}

export interface KeycloakResolverData extends HTTPResolverData {
  realm?: string;
}

export interface SCIMResolverData extends ResolverData {
  Authserver: string;
  Resourceserver: string;
  Client: string;
  Secret: string;
  Mapping: string;
}

export interface ResolverServiceInterface {
  resolversResource: HttpResourceRef<PiResponse<Resolvers> | undefined>;
  selectedResolverName: WritableSignal<string>;
  selectedResolverResource: HttpResourceRef<PiResponse<Resolvers> | undefined>;
  resolvers: Signal<Resolver[]>;
  resolverOptions: Signal<string[]>;
  editableResolvers: Signal<string[]>;
  userAttributes: Signal<string[]>;

  postResolverTest(data: ResolverData): Observable<PiResponse<boolean, { description: string }>>;
  postResolver(resolverName: string, data: ResolverData): Observable<PiResponse<number>>;
  deleteResolver(resolverName: string): Observable<PiResponse<number>>;
  getDefaultResolverConfig(resolverType: string): Observable<PiResponse<unknown>>;
}

@Injectable()
export class ResolverService implements ResolverServiceInterface {
  private readonly authService = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  readonly resolverBaseUrl = environment.proxyUrl + "/resolver/";

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.resolversResource.error(), "resolvers");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.selectedResolverResource.error(), "resolver details");
    });
  }
  resolversResource = httpResource<PiResponse<Resolvers>>(() => {
    if (!this.contentService.onAnyUsersRoute()) {
      return undefined;
    }
    if (!this.authService.actionAllowed("resolverread")) {
      return undefined;
    }
    return {
      url: this.resolverBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  selectedResolverName = signal<string>("");
  selectedResolverResource = httpResource<PiResponse<Resolvers>>(() => {
    const resolverName = this.selectedResolverName();
    if (resolverName === "") {
      return undefined;
    }
    return {
      url: this.resolverBaseUrl + encodeURIComponent(resolverName),
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  userAttributes = computed(() => {
    if (!this.selectedResolverResource.hasValue()) return [];
    const resolverResource = this.selectedResolverResource.value()?.result?.value;
    if (!resolverResource) return [];
    const resolverConfig = resolverResource[this.selectedResolverName()];
    const resolverType = resolverConfig?.type;
    let userInfo: Record<string, string> | string = {};

    switch (resolverType) {
      case "ldapresolver":
        userInfo = resolverConfig.data?.USERINFO || {};
        break;
      case "sqlresolver":
        userInfo = resolverConfig.data?.Map || {};
        break;
      case "httpresolver":
      case "entraidresolver":
      case "keycloakresolver":
        userInfo = resolverConfig.data?.attribute_mapping || {};
        break;
    }

    if (typeof userInfo === "string") {
      try {
        userInfo = JSON.parse(userInfo);
      } catch (error) {
        console.warn($localize`Failed to parse user info for resolver ${this.selectedResolverName()}` + ": ", error);
        userInfo = {};
      }
    }
    return Object.keys(userInfo);
  });
  resolverResourceValue = computed(() => {
    if (!this.resolversResource.hasValue()) return {};
    return this.resolversResource.value()?.result?.value || {};
  });
  resolvers = computed<Resolver[]>(() => {
    const resolvers = this.resolverResourceValue();
    return resolvers
      ? Object.entries(resolvers).map(([name, data]) => ({
          ...data,
          resolvername: data.resolvername || name
        }))
      : [];
  });
  resolverOptions = computed(() => {
    const resolvers = this.resolverResourceValue();
    return resolvers ? Object.keys(resolvers) : [];
  });

  editableResolvers = computed(() => {
    const resolvers = this.resolverResourceValue();
    if (!resolvers) return [];
    const editableResolverNames: string[] = [];
    for (const [name, resolver] of Object.entries(resolvers)) {
      const editable =
        resolver.data?.["Editable"] || resolver.data?.["editable"] || resolver.data?.["EDITABLE"] || false;
      if (parseBooleanValue(editable)) {
        editableResolverNames.push(name);
      }
    }
    return editableResolverNames;
  });

  postResolverTest(data: ResolverData = {}): Observable<PiResponse<boolean, { description: string }>> {
    return this.http
      .post<
        PiResponse<boolean, { description: string }>
      >(this.resolverBaseUrl + "test", data, { headers: this.authService.getHeaders() })
      .pipe(
        catchError((error) => {
          console.error("Error during resolver test:", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to test resolver. " + message);
          return throwError(() => error);
        })
      );
  }

  postResolver(resolverName: string, data: ResolverData): Observable<PiResponse<number>> {
    return this.http
      .post<
        PiResponse<number>
      >(this.resolverBaseUrl + encodeURIComponent(resolverName), data, { headers: this.authService.getHeaders() })
      .pipe(
        catchError((error) => {
          console.error(`Error during posting resolver ${resolverName}:`, error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to save resolver. " + message);
          return throwError(() => error);
        })
      );
  }

  deleteResolver(resolverName: string): Observable<PiResponse<number>> {
    return this.http
      .delete<
        PiResponse<number>
      >(this.resolverBaseUrl + encodeURIComponent(resolverName), { headers: this.authService.getHeaders() })
      .pipe(
        catchError((error) => {
          console.error(`Error during deleting resolver ${resolverName}:`, error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to delete resolver. " + message);
          return throwError(() => error);
        })
      );
  }

  getDefaultResolverConfig(resolverType: string): Observable<PiResponse<unknown>> {
    return this.http
      .get<
        PiResponse<unknown>
      >(this.resolverBaseUrl + encodeURIComponent(resolverType) + "/default", { headers: this.authService.getHeaders() })
      .pipe(
        catchError((error) => {
          console.error(`Error during getting default resolver config for ${resolverType}:`, error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to get default resolver config. " + message);
          return throwError(() => error);
        })
      );
  }
}
