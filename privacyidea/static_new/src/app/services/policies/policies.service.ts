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

export type PolicyActionDetail = {
  desc: string;
  type: string;
  group?: string;
  mainmenu?: string[];
  value?: string[] | number[];
};

export type ScopedPolicyActions = {
  [scopeName: string]: {
    [actionName: string]: PolicyActionDetail;
  };
};

export type PolicyActionGroups = {
  [scopeName: string]: {
    [group: string]: {
      [actionName: string]: PolicyActionDetail;
    };
  };
};

export type PoliciesList = PolicyDetail[];

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
  saveSelectedPolicy() {
    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy) return;
    this.createPolicy(selectedPolicy)
      .then((response) => {
        console.log("Policy created successfully: ", response);
        // Refresh the policies list
        this.allPoliciesRecource.reload();
      })
      .catch((error) => {
        console.error("Error creating policy: ", error);
      });
  }
  getDetailsOfAction(actionName: string): PolicyActionDetail | null {
    const actions = this.allPolicyActionsFlat();
    if (actionName && actions) {
      return actions[actionName] ?? null;
    }
    return null;
  }
  deselectPolicy() {
    this.selectedPolicy.set(null);
  }
  emptyPolicy: PolicyDetail = {
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
    scope: "admin",
    time: "",
    user: [],
    user_agents: [],
    user_case_insensitive: false
  };
  initializeEmptyPolicy() {
    const newPolicy = { ...this.emptyPolicy };
    this.selectedPolicy.set(newPolicy);
  }

  newPolicyEdited = computed(() => {
    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy) return false;
    // Check if selectedPolicy differs from emptyPolicy
    return JSON.stringify(selectedPolicy) !== JSON.stringify(this.emptyPolicy);
  });

  updateSelectedPolicy(args: { key: keyof PolicyDetail; value: any }) {
    const { key, value } = args;
    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy) return;
    const updatedPolicy = {
      ...selectedPolicy,
      [key]: value
    };
    console.log(`updated key ${key} to value ${value} in selectedPolicy`);
    console.log("updatedPolicy: ", updatedPolicy);
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
  selectedActionGroup: WritableSignal<string> = linkedSignal({
    source: () => this.policyActionGroupNames(),
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  selectedAction: WritableSignal<{ name: string; value: any } | null> = linkedSignal({
    source: () => this.getActionNamesOfSelectedGroup() ?? [],
    computation: (source, previous) => {
      const previousValue = previous?.value;
      if (source.length < 1) return null;
      if (previousValue && source.includes(previousValue.name)) return previous.value;
      const firstActionName = source[0];
      const defaultValue = this._getActionDetail(firstActionName)?.type === "bool" ? "true" : "";
      return { name: firstActionName, value: defaultValue };
    }
  });

  selectActionByName(actionName: string) {
    const actionNames = this.getActionNamesOfSelectedGroup();
    if (actionNames.includes(actionName)) {
      const defaultValue = this._getActionDetail(actionName)?.type === "bool" ? "true" : "";
      this.selectedAction.set({ name: actionName, value: defaultValue });
    }
  }

  updateSelectedActionValue(value: string | number) {
    const selectedAction = this.selectedAction();
    if (!selectedAction) return;
    this.selectedAction.set({ name: selectedAction.name, value: value });
  }

  // -----------------------------------
  // 2.3 Computed Signals (Derived State)
  // -----------------------------------

  policyActions = computed(() => {
    return this.policyActionResource.value()?.result?.value ?? {};
  });

  allPolicyActionsFlat = computed(() => {
    const policyActions = this.policyActionResource.value()?.result?.value;
    if (!policyActions) return {};
    const flat: { [actionName: string]: PolicyActionDetail } = {};
    for (const scope in policyActions) {
      const actions = policyActions[scope];
      for (const actionName in actions) {
        flat[actionName] = actions[actionName];
      }
    }
    return flat;
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
    const currentActions = this.selectedPolicy()?.action;
    if (!currentActions) return [];
    return Object.keys(currentActions);
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

  _getActionDetail = (actionName: string): PolicyActionDetail | null => {
    const actions = this.policyActions();
    const scope = this.selectedPolicy()?.scope;
    if (!scope) return null;
    if (actionName && actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  };

  selectedActionDetail: Signal<PolicyActionDetail | null> = computed(() => {
    const actionName = this.selectedAction()?.name;
    if (!actionName) return null;
    return this._getActionDetail(actionName);
  });

  // ===================================
  // 3. PUBLIC METHODS
  // ===================================

  // -----------------------------------
  // 3.1 API Methods
  // -----------------------------------

  createPolicy(data: PolicyDetail): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}${data.name}`, data, { headers }));
  }

  deletePolicy(name: string): Promise<PiResponse<number>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.delete<PiResponse<number>>(`${this.policyBaseUrl}${name}`, { headers }));
  }

  enablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}enable/${name}`, { headers }));
  }

  disablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}disable/${name}`, { headers }));
  }

  // -----------------------------------
  // 3.2 Local State Methods
  // -----------------------------------

  addActionToSelectedPolicy() {
    const selectedAction = this.selectedAction();
    const selectedActionDetail = this.selectedActionDetail();
    if (!selectedAction || !selectedActionDetail) return;
    if (this.alreadyAddedActionNames().includes(selectedAction.name)) return;
    if (!this.actionValueIsValid(selectedActionDetail, selectedAction.value)) return;

    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy) return;
    const currentAction = selectedPolicy.action || {};
    const updatedAction = {
      ...currentAction,
      [selectedAction.name]: selectedAction.value
    };
    const updatedPolicy = {
      ...selectedPolicy,
      action: updatedAction
    };
    console.log(`added action ${selectedAction.name} to selectedPolicy`);
    this.selectedPolicy.set(updatedPolicy);
  }

  removeActionFromSelectedPolicy(actionName: string) {
    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy || !selectedPolicy.action) return;
    const currentAction = selectedPolicy.action;
    if (!(actionName in currentAction)) return;
    const { [actionName]: _, ...updatedAction } = currentAction;
    const updatedPolicy = {
      ...selectedPolicy,
      action: Object.keys(updatedAction).length > 0 ? updatedAction : null
    };
    console.log(`removed action ${actionName} from selectedPolicy`);
    this.selectedPolicy.set(updatedPolicy);
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

  actionValueIsValid(action: PolicyActionDetail, value: string | number): boolean {
    if (!action) return false;
    const actionType = action.type;
    if (!actionType) return false;
    if (actionType === "int" && typeof value === "number") return Number.isInteger(value);
    if (typeof value !== "string") return false;

    if (actionType === "bool") {
      return value.toLowerCase() === "true" || value.toLowerCase() === "false";
    } else if (actionType === "int") {
      console.log("Validating int: ", value, !isNaN(Number(value)), Number.isInteger(Number(value)));
      return value.trim().length > 0 && !isNaN(Number(value)) && Number.isInteger(Number(value));
    } else if (actionType === "str") {
      return value.trim().length > 0;
    } else if (actionType === "text") {
      return value.trim().length > 0;
    }
    return false;
  }
}
