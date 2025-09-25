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

import { HttpClient, httpResource } from "@angular/common/http";
import { computed, effect, inject, Injectable, signal } from "@angular/core";
import { lastValueFrom } from "rxjs";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { environment } from "../../../environments/environment";

// JSON Parameters:
//         name (basestring) – name of the policy
//         scope – the scope of the policy like “admin”, “system”, “authentication” or “selfservice”
//         priority – the priority of the policy
//         description – a description of the policy
//         adminrealm – Realm of the administrator. (only for admin scope)
//         adminuser – Username of the administrator. (only for admin scope)
//         action – which action may be executed
//         realm – For which realm this policy is valid
//         resolver – This policy is valid for this resolver
//         user – The policy is valid for these users. string with wild cards or list of strings
//         time – on which time does this policy hold
//         pinode – The privacyIDEA node (or list of nodes) for which this policy is valid
//         client (IP address with subnet) – for which requesting client this should be
//         active – bool, whether this policy is active or not
//         check_all_resolvers – bool, whether all all resolvers in which the user exists should be checked with this policy.
//         conditions – a (possibly empty) list of conditions of the policy. Each condition is encoded as a list with 5 elements: [section (string), key (string), comparator (string), value (string), active (boolean)] Hence, the conditions parameter expects a list of lists. When privacyIDEA checks if a defined policy should take effect, all conditions of the policy must be fulfilled for the policy to match. Note that the order of conditions is not guaranteed to be preserved.

// Return:

//     a json result with success or error
// Status Codes:
//         200 OK – Policy created or modified.
//         401 Unauthorized – Authentication failed

export interface PolicyCreateData {
  name: string; // name of the policy
  scope: "admin" | "system" | "authentication" | "selfservice"; // the scope of the policy like “admin”, “system”, “authentication” or “selfservice”
  priority: number; // the priority of the policy
  description?: string; // a description of the policy
  adminrealm?: string; // Realm of the administrator. (only for admin scope)
  adminuser?: string; // Username of the administrator. (only for admin scope)
  action?: string | string[]; // which action may be executed
  realm?: string; // For which realm this policy is valid
  resolver?: string; // This policy is valid for this resolver
  user?: string | string[]; // The policy is valid for these users. string with wild cards or list of strings
  time?: string; // on which time does this policy hold
  pinode?: string | string[]; // The privacyIDEA node (or list of nodes) for which this policy is valid
  client?: string; // (IP address with subnet) – for which requesting client this should be
  active?: boolean; // whether this policy is active or not
  check_all_resolvers?: boolean; // whether all all resolvers in which the user exists should be checked with this policy.
  conditions?: [string, string, string, string, boolean][]; // a (possibly empty) list of conditions of the policy. Each condition is encoded as a list with 5 elements: [section (string), key (string), comparator (string), value (string), active (boolean)] Hence, the conditions parameter expects a list of lists. When privacyIDEA checks if a defined policy should take effect, all conditions of the policy must be fulfilled for the policy to match. Note that the order of conditions is not guaranteed to be preserved.
}

export type PoliciesList = PolicyDetail[];

export type PolicyDetail = {
  action: Object;
  active: boolean;
  client: string;
  name: string;
  realm: string;
  resolver: string;
  scope: string;
  time: string;
  user: string | string[];
};

export interface PoliciesServiceInterface {}

@Injectable({
  providedIn: "root"
})
export class PoliciesService implements PoliciesServiceInterface {
  getPolicyScopes(): string[] {
    throw new Error("Method not implemented.");
  }
  readonly policyBaseUrl = environment.proxyUrl + "/policy/";

  private readonly http: HttpClient = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  // selectedPolicy = signal<string>("");
  selectedPolicyScope = signal<string>("");

  policyDefinitions = httpResource(() => ({
    url: `${this.policyBaseUrl}defs`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  allPolicies = computed(() => {
    return this.allPoliciesRecource.value()?.result?.value ?? [];
  });
  // selectedPolicyRecource = httpResource<PiResponse<PolicyDetail[]>>(() => ({
  //   url: `${this.policyBaseUrl}/${this.selectedPolicy()}`,
  //   method: "GET",
  //   headers: this.authService.getHeaders()
  // }));
  allPoliciesRecource = httpResource<PiResponse<PolicyDetail[]>>(() => ({
    url: `${this.policyBaseUrl}`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));
  // `/policy/${this.selectedPolicy()}`

  constructor() {
    // effect(() => {
    //   console.log(this.selectedPolicy());
    // });
    // effect(() => {
    //   console.log(this.selectedPolicyDetails.value());
    // });
    effect(() => {
      console.log(this.allPolicies());
    });
  }

  enablePolicy(name: string): Promise<PiResponse<any>> {
    return lastValueFrom(this.http.post<PiResponse<any>>(`${environment.proxyUrl}enable/${name}`, {}));
  }

  disablePolicy(name: string): Promise<PiResponse<any>> {
    return lastValueFrom(this.http.post<PiResponse<any>>(`${environment.proxyUrl}disable/${name}`, {}));
  }

  createPolicy(data: PolicyCreateData): Promise<PiResponse<any>> {
    // Example request:
    // In this example a policy “pol1” is created.
    // ******************************
    // * POST /policy/pol1 HTTP/1.1 *
    // * Host: example.com          *
    // * Accept: application/json   *
    // *                            *
    // * scope=admin                *
    // * realm=realm1               *
    // * action=enroll, disable     *
    // ******************************

    return lastValueFrom(this.http.post<PiResponse<any>>(`${environment.proxyUrl}${data.name}`, data));
  }

  deletePolicy(name: string): Promise<PiResponse<number>> {
    return lastValueFrom(this.http.delete<PiResponse<number>>(`${environment.proxyUrl}${name}`));
  }
}
