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
import { environment } from "@env/environment";
import { PiResponse } from "../../app.component";
import { AuthService } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { catchError, Observable, throwError } from "rxjs";

export type ResolverType =
  "ldapresolver"
  | "sqlresolver"
  | "passwdresolver"
  | "scimresolver"
  | "httpresolver"
  | "entraidresolver"
  | "keycloakresolver";

export interface ResolverData {
  [key: string]: any;
}

export type Resolvers = { [key: string]: Resolver };

export interface Resolver {
  censor_keys: string[];
  data: ResolverData;
  resolvername: string;
  type: ResolverType;
}

export interface LDAPResolverData extends ResolverData {
  LDAPURI: string;
  LDAPBASE: string;
  AUTHTYPE: string;
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

export interface HTTPResolverData extends ResolverData {
  base_url?: string;
  attribute_mapping?: { [key: string]: string };
  Editable?: boolean;
  verify_tls?: boolean;
  tls_ca_path?: string;
  timeout?: number;
  advanced?: boolean;
  config_get_user_list?: any;
  config_get_user_by_id?: any;
  config_get_user_by_name?: any;
  config_create_user?: any;
  config_edit_user?: any;
  config_delete_user?: any;
  config_authorization?: any;
  config_user_auth?: any;
  config_get_user_groups?: any;
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
  selectedResolverResource: HttpResourceRef<PiResponse<any> | undefined>;
  resolvers: Signal<Resolver[]>;
  resolverOptions: Signal<string[]>;

  postResolverTest(data: any): Observable<PiResponse<any, any>>;

  postResolver(resolverName: string, data: any): Observable<PiResponse<any, any>>;

  deleteResolver(resolverName: string): Observable<PiResponse<any, any>>;

  getDefaultResolverConfig(resolverType: string): Observable<PiResponse<any, any>>;
}

@Injectable({
  providedIn: "root"
})
export class ResolverService implements ResolverServiceInterface {
  readonly resolverBaseUrl = environment.proxyUrl + "/resolver/";
  private readonly authService = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly http: HttpClient = inject(HttpClient);
  resolversResource = httpResource<PiResponse<Resolvers>>(() => {
    if (!this.contentService.onAnyUsersRoute()) {
      return undefined;
    }
    return {
      url: this.resolverBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  selectedResolverName = signal<string>("");
  selectedResolverResource = httpResource<PiResponse<any>>(() => {
    const resolverName = this.selectedResolverName();
    if (resolverName === "") {
      return undefined;
    }
    return {
      url: this.resolverBaseUrl + resolverName,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  resolvers = computed<Resolver[]>(() => {
    const resolvers = this.resolversResource.value()?.result?.value;
    return resolvers ? Object.entries(resolvers).map(([name, data]) => ({
      ...data,
      resolvername: data.resolvername || name
    })) : [];
  });
  resolverOptions = computed(() => {
    const resolvers = this.resolversResource.value()?.result?.value;
    return resolvers ? Object.keys(resolvers) : [];
  });

  postResolverTest(data: any = {}): Observable<PiResponse<any, any>> {
    return this.http.post<PiResponse<any, any>>(this.resolverBaseUrl + "test", data, { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error("Error during resolver test:", error);
        return throwError(() => error);
      })
    );
  }

  postResolver(resolverName: string, data: any): Observable<PiResponse<any, any>> {
    return this.http.post<PiResponse<any, any>>(this.resolverBaseUrl + resolverName, data, { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error(`Error during posting resolver ${resolverName}:`, error);
        return throwError(() => error);
      })
    );
  }

  deleteResolver(resolverName: string): Observable<PiResponse<any, any>> {
    return this.http.delete<PiResponse<any, any>>(this.resolverBaseUrl + resolverName, { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error(`Error during deleting resolver ${resolverName}:`, error);
        return throwError(() => error);
      })
    );
  }

  getDefaultResolverConfig(resolverType: string): Observable<PiResponse<any, any>> {
    return this.http.get<PiResponse<any, any>>(this.resolverBaseUrl + resolverType + "/default", { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error(`Error during getting default resolver config for ${resolverType}:`, error);
        return throwError(() => error);
      })
    );
  }
}
