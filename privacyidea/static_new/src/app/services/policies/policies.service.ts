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
import { computed, effect, inject, Injectable, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { lastValueFrom } from "rxjs";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { environment } from "../../../environments/environment";

export type PolicyAction = {
  desc: string;
  type: string;
  group?: string;
  mainmenu?: string[];
  value?: string[] | number[];
};

export type ScopedPolicyActions = {
  [scopeName: string]: {
    [actionName: string]: PolicyAction;
  };
};

export type PolicyActionGroups = {
  [scopeName: string]: {
    [group: string]: {
      [actionName: string]: PolicyAction;
    };
  };
};

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
//         conditions – a (possibly empty) list of conditions of the policy.
//                     Each condition is encoded as a list with 5 elements: [section (string), key (string), comparator (string), value (string), active (boolean)] Hence, the conditions parameter expects a list of lists.
//                     When privacyIDEA checks if a defined policy should take effect, all conditions of the policy must be fulfilled for the policy to match. Note that the order of conditions is not guaranteed to be preserved.

// Return:

//     a json result with success or error
// Status Codes:
//         200 OK – Policy created or modified.
//         401 Unauthorized – Authentication failed

export type PoliciesList = PolicyDetail[];

/*
{
	"1": {
		"action": {
			"push_registration_url": "http://192.168.178.139:5000/ttype/push",
			"push_ssl_verify": "0"
		},
		"active": true,
		"adminrealm": [],
		"adminuser": [],
		"check_all_resolvers": false,
		"client": [],
		"conditions": [],
		"description": null,
		"name": "push_token1",
		"pinode": [],
		"priority": 1,
		"realm": [],
		"resolver": [],
		"scope": "enrollment",
		"time": "",
		"user": [],
		"user_agents": [],
		"user_case_insensitive": false
	}
}
*/

export type PolicyDetail = {
  action: { [actionName: string]: string } | null;
  active: boolean;
  adminrealm: string[];
  adminuser: string[];
  check_all_resolvers: boolean;
  client: string[];
  conditions: [string, string, string, string, boolean][];
  description: string | null;
  name: string;
  pinode: string[];
  priority: number;
  realm: string[];
  resolver: string[];
  scope: string;
  time: string;
  user: string[];
  user_agents: string[];
  user_case_insensitive: boolean;
};

export interface PoliciesServiceInterface {}

@Injectable({
  providedIn: "root"
})
export class PolicyService implements PoliciesServiceInterface {
  deselectPolicy() {
    this.selectedPolicy.set(null);
  }
  selectEmptypolicy() {
    this.selectedPolicy.set({
      action: null,
      active: true,
      adminrealm: [],
      adminuser: [],
      check_all_resolvers: false,
      client: [],
      conditions: [],
      description: null,
      name: "",
      pinode: [],
      priority: 100,
      realm: [],
      resolver: [],
      scope: this.allPolicyScopes()[0] || "admin",
      time: "",
      user: [],
      user_agents: [],
      user_case_insensitive: false
    });
  }

  updateSelectedPolicy(args: { key: keyof PolicyDetail; value: any }) {
    const { key, value } = args;
    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy) return;
    const updatedPolicy = {
      ...selectedPolicy,
      key: value
    };
    console.log(`updated key ${key} to value ${value} in selectedPolicy`);
    this.selectedPolicy.set(updatedPolicy);
  }

  // ===================================
  // 1. PROPERTIES & INJECTED SERVICES
  // ===================================

  readonly policyBaseUrl = environment.proxyUrl + "/policy/";

  private readonly http: HttpClient = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  // ===================================
  // 2. STATE (RESOURCES & SIGNALS)
  // ===================================

  // -----------------------------------
  // 2.1 API Resources
  // -----------------------------------

  // GET /policy/defs
  policyActionResource = httpResource<PiResponse<ScopedPolicyActions>>(() => ({
    url: `${this.policyBaseUrl}defs`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  policyDefinitions = httpResource(() => ({
    url: `${this.policyBaseUrl}defs`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  allPoliciesRecource = httpResource<PiResponse<PolicyDetail[]>>(() => ({
    url: `${this.policyBaseUrl}`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  // -----------------------------------
  // 2.2 Writable Signals (State)
  // -----------------------------------

  // Signals for selecting and editing selected policy
  selectedPolicy = signal<PolicyDetail | null>(null);

  // Signals for action handling
  actionFilter = signal<string>("");
  currentActions = signal<{ actionName: string; value: string }[]>([]);
  selectedActionGroup: WritableSignal<string> = linkedSignal({
    source: () => this.policyActionGroupNames(),
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  selectedActionName: WritableSignal<string> = linkedSignal({
    source: computed(() => this.getActionNamesOfSelectedGroup() ?? []),
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  selectedActionValue = signal("");

  // -----------------------------------
  // 2.3 Computed Signals (Derived State)
  // -----------------------------------

  policyActions = computed(() => {
    return this.policyActionResource.value()?.result?.value ?? {};
  });

  allPolicyScopes = computed(() => {
    const policyActions = this.policyActionResource.value()?.result?.value;
    if (!policyActions) return [];
    return Object.keys(policyActions);
  });

  policyActionsByGroup = computed<PolicyActionGroups>(() => {
    const policyActions = this.policyActionResource.value()?.result?.value;
    if (!policyActions) return {};
    const grouped: PolicyActionGroups = {};
    for (const scope in policyActions) {
      const actions = policyActions[scope];
      grouped[scope] = {};
      for (const actionName in actions) {
        const action = actions[actionName];
        const group = action.group || "Other";
        if (!grouped[scope][group]) {
          grouped[scope][group] = {};
        }
        grouped[scope][group][actionName] = action;
      }
    }
    return grouped;
  });

  alreadyAddedActionNames = computed(() => {
    return this.currentActions().map((a) => a.actionName);
  });

  policyActionsByGroupFiltered = computed<PolicyActionGroups>(() => {
    // Also filter out already added actions
    const alreadyAddedActionNames = this.alreadyAddedActionNames();
    if (!this.actionFilter() && alreadyAddedActionNames.length === 0) {
      return this.policyActionsByGroup();
    }
    const policyActions = this.policyActionResource.value()?.result?.value;
    if (!policyActions) return {};
    const grouped: PolicyActionGroups = {};
    const filterValue = this.actionFilter().toLowerCase();
    for (const scope in policyActions) {
      const actions = policyActions[scope];
      grouped[scope] = {};
      for (const actionName in actions) {
        if (alreadyAddedActionNames.includes(actionName)) {
          continue;
        }
        const action = actions[actionName];
        if (!actionName.toLowerCase().includes(filterValue)) {
          continue;
        }
        const group = action.group || "Other";
        if (!grouped[scope][group]) {
          grouped[scope][group] = {};
        }
        grouped[scope][group][actionName] = action;
      }
    }
    return grouped;
  });

  allPolicies = computed(() => {
    return this.allPoliciesRecource.value()?.result?.value ?? [];
  });

  policyActionGroupNames: Signal<string[]> = computed(() => {
    const selectedScope = this.selectedPolicy()?.scope;
    console.log("selectedScope: ", selectedScope);
    if (!selectedScope) return [];
    const policyActionGroupFiltered = this.policyActionsByGroupFiltered()[selectedScope];
    console.log("policyActionGroupFiltered: ", policyActionGroupFiltered);
    if (!policyActionGroupFiltered) return [];
    return Object.keys(policyActionGroupFiltered);
  });

  selectedAction: Signal<PolicyAction | null> = computed(() => {
    const actions = this.policyActions();
    const actionName = this.selectedActionName();
    const scope = this.selectedPolicy()?.scope; // Only check for actions[scope][actionName] if actions[scope] exists
    if (!scope) return null;
    if (actionName && actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  });

  // ===================================
  // 3. PUBLIC METHODS
  // ===================================

  // -----------------------------------
  // 3.1 API Methods
  // -----------------------------------

  createPolicy(data: PolicyDetail): Promise<PiResponse<any>> {
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

  enablePolicy(name: string): Promise<PiResponse<any>> {
    return lastValueFrom(this.http.post<PiResponse<any>>(`${environment.proxyUrl}enable/${name}`, {}));
  }

  disablePolicy(name: string): Promise<PiResponse<any>> {
    return lastValueFrom(this.http.post<PiResponse<any>>(`${environment.proxyUrl}disable/${name}`, {}));
  }

  // -----------------------------------
  // 3.2 Local State Methods
  // -----------------------------------

  addAction() {
    const actionName = this.selectedActionName();
    const selectedAction = this.selectedAction();
    const actionValue = this.selectedActionValue();
    if (this.alreadyAddedActionNames().includes(actionName) || selectedAction === null) return;
    if (!this.actionValueIsValid(selectedAction, actionValue)) return;

    const newAction = {
      actionName: actionName,
      value: actionValue
    };

    this.currentActions.set([...this.currentActions(), newAction]);
  }

  updateAction() {
    const actionName = this.selectedActionName();
    const selectedAction = this.selectedAction();
    const actionValue = this.selectedActionValue();
    if (!this.alreadyAddedActionNames().includes(actionName) || selectedAction === null) return;
    if (!this.actionValueIsValid(selectedAction, actionValue)) return;
    const updatedActions = this.currentActions().map((a) =>
      a.actionName === actionName ? { actionName: a.actionName, value: actionValue } : a
    );
    this.currentActions.set(updatedActions);
  }

  // -----------------------------------
  // 3.3 Helper Methods
  // -----------------------------------

  isScopeChangeable(policy: PolicyDetail): boolean {
    return !policy.action;
  }

  getActionNamesOfSelectedGroup(): string[] {
    const group: string = this.selectedActionGroup();
    const actionsByGroup = this.policyActionsByGroupFiltered();
    const scope = this.selectedPolicy()?.scope;
    if (!scope || !actionsByGroup[scope]) return [];
    return Object.keys(actionsByGroup[scope][group] || {});
  }

  actionValueIsValid(action: PolicyAction, value: string | number): boolean {
    if (!action) return false;
    const actionType = action.type;
    if (!actionType) return false;
    if (actionType === "int" && typeof value === "number") return Number.isInteger(value);
    if (typeof value !== "string") return false;

    if (actionType === "bool") {
      return value.toLowerCase() === "true" || value.toLowerCase() === "false";
    } else if (actionType === "int") {
      return !isNaN(Number(value)) && Number.isInteger(Number(value));
    } else if (actionType === "str") {
      return value.trim().length > 0;
    }
    return false;
  }
}
