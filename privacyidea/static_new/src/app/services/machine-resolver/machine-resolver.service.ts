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

import { computed, inject, Injectable, Signal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { HttpClient, httpResource } from "@angular/common/http";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { PiResponse } from "../../app.component";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { lastValueFrom } from "rxjs";

export type MachineResolvers = {
  [key: string]: MachineResolver;
};
export interface MachineResolverData {
  resolver: string;
  type: string;
}

export interface MachineResolver {
  resolvername: string;
  type: string;
  data: MachineResolverData;
}

export interface HostsMachineResolverData extends MachineResolverData {
  filename: string;
  type: "hosts";
}

export interface HostsMachineResolver extends MachineResolver {
  type: "hosts";
  data: HostsMachineResolverData;
}

export interface LdapMachineResolverData extends MachineResolverData {
  type: "ldap";
  AUTHTYPE: string;
  TLS_VERIFY: boolean;
  START_TLS: boolean;
  LDAPURI: string;
  TLS_CA_FILE: string;
  LDAPBASE: string;
  BINDDN: string;
  BINDPW: string;
  TIMEOUT: string;
  SIZELIMIT: string;
  SEARCHFILTER: string;
  IDATTRIBUTE: string;
  IPATTRIBUTE: string;
  HOSTNAMEATTRIBUTE: string;
  NOREFERRALS: "True" | "False";
}

export interface LdapMachineResolver extends MachineResolver {
  type: "ldap";
  data: LdapMachineResolverData;
}

export interface MachineResolverServiceInterface {
  readonly allMachineResolverTypes: string[];
  readonly machineResolvers: Signal<MachineResolver[]>;

  postMachineResolver(resolver: MachineResolver): Promise<void>;
  postTestMachineResolver(resolver: MachineResolver): Promise<void>;
  deleteMachineResolver(name: string): Promise<void>;
}

@Injectable({
  providedIn: "root"
})
export class MachineResolverService implements MachineResolverServiceInterface {
  readonly allMachineResolverTypes: string[] = ["hosts", "ldap"];
  readonly machineResolverBaseUrl = environment.proxyUrl + "/machineresolver/";

  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly http: HttpClient = inject(HttpClient);

  readonly machineResolverResource = httpResource<PiResponse<MachineResolvers>>(() => {
    if (!this.authService.actionAllowed("mresolverread")) {
      this.notificationService.openSnackBar("You are not allowed to read Machine Resolvers.");
      return undefined;
    }
    return {
      url: `${this.machineResolverBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly machineResolvers = computed<MachineResolver[]>(() => {
    const res = this.machineResolverResource.value();
    return res?.result?.value ? Object.values(res.result.value) : [];
  });

  async postTestMachineResolver(resolver: MachineResolver): Promise<void> {
    if (!this.authService.actionAllowed("mresolverwrite")) {
      this.notificationService.openSnackBar("You are not allowed to update Machine Resolvers.");
      throw new Error("not-allowed");
    }
    const url = `${this.machineResolverBaseUrl}test`;
    const request = this.http.post<PiResponse<any>>(url, resolver.data, { headers: this.authService.getHeaders() });
    return lastValueFrom(request)
      .then(() => {})
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to update machineResolver. " + message);
        throw new Error("post-failed");
      });
  }

  async postMachineResolver(resolver: MachineResolver): Promise<void> {
    if (!this.authService.actionAllowed("mresolverwrite")) {
      this.notificationService.openSnackBar("You are not allowed to update Machine Resolvers.");
      throw new Error("not-allowed");
    }
    const url = `${this.machineResolverBaseUrl}${resolver.resolvername}`;
    const request = this.http.post<PiResponse<any>>(url, resolver.data, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar(`Successfully updated machineResolver.`);
        this.machineResolverResource.reload();
      })
      .catch((error) => {
        console.warn("Failed to update machineResolver:", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to update machineResolver. " + message);
        throw new Error("post-failed");
      });
  }

  async deleteMachineResolver(name: string): Promise<void> {
    if (!this.authService.actionAllowed("mresolverdelete")) {
      this.notificationService.openSnackBar("You are not allowed to delete Machine Resolvers.");
      throw new Error("not-allowed");
    }
    const request = this.http.delete<PiResponse<any>>(`${this.machineResolverBaseUrl}${name}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar(`Successfully deleted machineResolver: ${name}.`);
        this.machineResolverResource.reload();
      })
      .catch((error) => {
        console.warn("Failed to delete machineResolver:", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete machineResolver. " + message);
        throw new Error("delete-failed");
      });
  }
}
