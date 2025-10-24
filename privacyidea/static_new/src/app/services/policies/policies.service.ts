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
import { computed, inject, Injectable, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { lastValueFrom } from "rxjs";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";

export type ActionType = "bool" | "int" | "str" | "text";
export type PolicyActionDetail = {
  desc: string;
  type: ActionType;
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

// const asd = {
//   action: ["container_challenge_ttl=12"],
//   scope: "container",
//   realm: [
//     "defrealm",
//     "realm1",
//     "realm2",
//     "realm3",
//     "realm4asdfsadfasdfasdfsadfasdfasfasfdsadfasdfsafdasdfasdfsadfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfsadfasdfasdfasd"
//   ],
//   resolver: ["deflocal"],
//   user: "asd",
//   active: true,
//   check_all_resolvers: false,
//   user_case_insensitive: true,
//   client: "10.0.0.0/8",
//   time: "Mon: 1-12",
//   description: "",
//   priority: 1,
//   conditions: [
//     ["userinfo", "asd", "equals", "asd", true, "raise_error"],
//     ["userinfo", "asf", "equals", "asd", true, "raise_error"],
//     ["userinfo", "asd", "equals", "asf", true, "raise_error"],
//     ["userinfo", "asd", "equals", "asd", true, "raise_error"]
//   ],
//   pinode: ["localnode", "localnode", "localnode"],
//   user_agents: [
//     "privacyidea-cp",
//     "privacyIDEA-Keycloak",
//     "PrivacyIDEA-ADFS",
//     "simpleSAMLphp",
//     "PAM",
//     "privacyIDEA-Shibboleth",
//     "privacyidea-nextcloud",
//     "FreeRADIUS",
//     "privacyIDEA-LDAP-Proxy",
//     "privacyIDEA-App",
//     "567"
//   ],
//   name: "test",
//   adminrealm: []
// };

export type PolicyDetail = {
  action: { [actionName: string]: string } | null;
  active: boolean;
  adminrealm: string[];
  adminuser: string[];
  check_all_resolvers: boolean;
  client: string[];
  conditions: AdditionalCondition[];
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

export type AdditionalCondition = [SectionOption, string, ComporatorOption, string, boolean, HandleMissigDataOption];

export type SectionOption =
  | "HTTP Environment"
  | "HTTP Request header"
  | "Requst Data"
  | "container"
  | "container_info"
  | "token"
  | "tokeninfo"
  | "userinfo";

/**
 * Get a list of strings from the SectionOption type.
 * @returns {string[]} The list of strings.
 */
export const allSectionOptions: SectionOption[] = [
  "HTTP Environment",
  "HTTP Request header",
  "Requst Data",
  "container",
  "container_info",
  "token",
  "tokeninfo",
  "userinfo"
] as SectionOption[];

export type ComporatorOption =
  | "!contains"
  | "!date_within_last"
  | "!equals"
  | "!in"
  | "!matches"
  | "!string_contains"
  | "<"
  | ">"
  | "contains"
  | "date_after"
  | "date_before"
  | "date_within_last"
  | "equals"
  | "in"
  | "matches"
  | "string_contains";

export const allComporatorOptions: ComporatorOption[] = [
  "!contains",
  "!date_within_last",
  "!equals",
  "!in",
  "!matches",
  "!string_contains",
  "<",
  ">",
  "contains",
  "date_after",
  "date_before",
  "date_within_last",
  "equals",
  "in",
  "matches",
  "string_contains"
];

export type HandleMissigDataOption = "raise_error" | "condition_is_false" | "condition_is_true";

export const allHandleMissingDataOptions: HandleMissigDataOption[] = [
  "raise_error",
  "condition_is_false",
  "condition_is_true"
];

export interface PoliciesServiceInterface {}

@Injectable({
  providedIn: "root"
})
export class PolicyService implements PoliciesServiceInterface {
  updateActionInSelectedPolicy() {
    const selectedPolicy = this.selectedPolicy();
    const selectedAction = this.selectedAction();
    const actionName = selectedAction?.name;
    const actionValue = selectedAction?.value;
    if (!selectedPolicy || !actionName || actionValue === undefined) return;
    if (!selectedPolicy || !selectedPolicy.action) return;
    const currentAction = selectedPolicy.action;
    if (!(actionName in currentAction)) return;
    const updatedAction = {
      ...currentAction,
      [actionName]: actionValue
    };
    this.updateSelectedPolicy({ action: updatedAction });
  }
  private readonly contentService: ContentServiceInterface = inject(ContentService);

  updateActionValue(actionName: string, newValue: boolean) {
    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy || !selectedPolicy.action) return;
    const currentAction = selectedPolicy.action;
    if (!(actionName in currentAction)) return;
    const updatedAction = {
      ...currentAction,
      [actionName]: newValue.toString()
    };
    this.updateSelectedPolicy({ action: updatedAction });
  }
  viewMode: WritableSignal<"view" | "edit" | "new"> = linkedSignal({
    source: () => {
      this.contentService.routeUrl();
    },
    computation: (_) => "view"
  });

  selectPolicyByName(policyName: string) {
    const policy = this.allPolicies().find((p) => p.name === policyName);
    if (policy) {
      this.selectPolicy(policy);
    }
  }
  canSaveSelectedPolicy(): boolean {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    if (!policy.name || policy.name.trim() === "") return false;
    if (!policy.scope || policy.scope.trim() === "") return false;
    if (!this.selectedPolicyHasActions()) return false;
    return true;
  }

  selectedPolicyHasActions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return policy?.action && Object.keys(policy.action).length > 0;
  });

  selectedPolicyHasUserConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    if (policy.realm && policy.realm.length > 0) return true;
    if (policy.resolver && policy.resolver.length > 0) return true;
    if (policy.user && policy.user.length > 0) return true;
    return false;
  });

  selectedPolicyHasNodeConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    if (policy.pinode && policy.pinode.length > 0) return true;
    if (policy.time && policy.time.length > 0) return true;
    if (policy.client && policy.client.length > 0) return true;
    if (policy.user_agents && policy.user_agents.length > 0) return true;
    return false;
  });

  selectedPolicyHasAdditionalConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return policy.conditions && policy.conditions.length > 0;
  });

  selectedPolicyHasConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    if (this.selectedPolicyHasUserConditions()) return true;
    if (this.selectedPolicyHasNodeConditions()) return true;
    if (this.selectedPolicyHasAdditionalConditions()) return true;
    return false;
  });

  savePolicyEdits() {
    const selectedPolicy = this.selectedPolicy();
    const oldPolicyName = this.selectedPolicyOriginal()?.name;
    if (!selectedPolicy || !oldPolicyName) return;

    const allPolicies = this.allPolicies();
    if (oldPolicyName) {
      const index = allPolicies.findIndex((p) => p.name === oldPolicyName);
      if (index !== -1) {
        allPolicies[index] = selectedPolicy;
      }
    }

    if (this.viewMode() === "new") {
      this.createPolicy(selectedPolicy)
        .then((response) => {
          // Refresh the policies list
          this.allPoliciesRecource.reload();
        })
        .catch((error) => {
          console.error("Error creating policy: ", error);
        });
    } else if (this.viewMode() === "edit") {
      this.updatePolicy(oldPolicyName, selectedPolicy)
        .then((response) => {
          // Refresh the policies list
          this.allPoliciesRecource.reload();
        })
        .catch((error) => {
          console.error("Error updating policy: ", error);
        });
    }

    this.selectPolicy(selectedPolicy);
    this.viewMode.set("view");
  }
  getDetailsOfAction(actionName: string): PolicyActionDetail | null {
    const actions = this.allPolicyActionsFlat();
    if (actionName && actions) {
      return actions[actionName] ?? null;
    }
    return null;
  }
  deselectPolicy(name: string) {
    if (this.selectedPolicyOriginal()?.name !== name) return;
    this._selectedPolicy.set(null);
    this._selectedPolicyOriginal.set(null);
    this.viewMode.set("view");
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
    priority: 1,
    realm: [],
    resolver: [],
    scope: "",
    time: "",
    user: [],
    user_agents: [],
    user_case_insensitive: false
  };
  initializeNewPolicy() {
    this._selectedPolicy.set({ ...this.emptyPolicy });
    this._selectedPolicyOriginal.set({ ...this.emptyPolicy });
    this.viewMode.set("new");
  }

  isPolicyEdited = computed(() => {
    const selectedPolicy = this.selectedPolicy();
    const originalPolicy = this.selectedPolicyOriginal();
    if (!selectedPolicy || !originalPolicy) return false;
    if (JSON.stringify(originalPolicy) === JSON.stringify(this.emptyPolicy)) {
      // remove scope temporarily and then compare to ignore scope changes
      const { scope: _, ...selectedWithoutScope } = selectedPolicy;
      const { scope: __, ...originalWithoutScope } = originalPolicy;
      return JSON.stringify(selectedWithoutScope) !== JSON.stringify(originalWithoutScope);
    } else {
      return JSON.stringify(selectedPolicy) !== JSON.stringify(originalPolicy);
    }
  });
  selectPolicy(policy: PolicyDetail) {
    this._selectedPolicy.set(policy);
    this._selectedPolicyOriginal.set({ ...policy });
    this.viewMode.set("view");
  }

  updateSelectedPolicy(args: Partial<PolicyDetail>) {
    const selectedPolicy = this.selectedPolicy();
    console.log("Updating selected policy with args:", args);
    console.log("Current selected policy before update:", selectedPolicy);
    if (!selectedPolicy) return;
    const updatedPolicy = {
      ...selectedPolicy,
      ...args
    };
    console.log("Updated selected policy:", updatedPolicy);
    this._selectedPolicy.set(updatedPolicy);
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
  private _selectedPolicy = signal<PolicyDetail | null>(null);
  selectedPolicy = computed(() => {
    console.log("Selected policy changed:", this._selectedPolicy());
    return this._selectedPolicy();
  });
  private _selectedPolicyOriginal = signal<PolicyDetail | null>(null);
  selectedPolicyOriginal = computed(() => this._selectedPolicyOriginal());

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

  updateSelectedActionValue(value: any) {
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
    const currentActions = this._selectedPolicy()?.action;
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

  _allPolicies = computed(() => {
    return this.allPoliciesRecource.value()?.result?.value ?? [];
  });
  allPolicies = linkedSignal({
    source: () => this._allPolicies(),
    computation: (source) => {
      return source.sort((a, b) => a.priority - b.priority);
    }
  });

  policyActionGroupNames: Signal<string[]> = computed(() => {
    const selectedScope = this._selectedPolicy()?.scope;
    if (!selectedScope) return [];
    const policyActionGroupFiltered = this.policyActionsByGroupFiltered()[selectedScope];
    if (!policyActionGroupFiltered) return [];
    return Object.keys(policyActionGroupFiltered);
  });

  _getActionDetail = (actionName: string): PolicyActionDetail | null => {
    const actions = this.policyActions();
    const scope = this._selectedPolicy()?.scope;
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

  createPolicy(policyData: PolicyDetail): Promise<PiResponse<any>> {
    const allPolicies = this.allPolicies();
    allPolicies.push({ ...policyData });
    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post<PiResponse<any>>(`${this.policyBaseUrl}${policyData.name}`, policyData, { headers })
    );
  }

  async updatePolicy(oldPolicyName: String, policyData: PolicyDetail): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    let patchNameRespone: PiResponse<any> | null = null;
    if (oldPolicyName !== policyData.name) {
      patchNameRespone = await lastValueFrom(
        this.http.patch<PiResponse<any>>(`${this.policyBaseUrl}${oldPolicyName}`, policyData, { headers })
      );
    }
    if (patchNameRespone && patchNameRespone.result?.error) {
      return patchNameRespone;
    }
    const response = await lastValueFrom(
      this.http.post<PiResponse<any>>(`${this.policyBaseUrl}${policyData.name}`, policyData, { headers })
    );
    return response;
  }

  deletePolicy(name: string): Promise<PiResponse<number>> {
    const allPolicies = this.allPolicies();
    if (!allPolicies) return Promise.reject("No policies found");
    const policy = allPolicies.find((p) => p.name === name);
    if (!policy) return Promise.reject(`Policy with name ${name} not found`);

    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.delete<PiResponse<number>>(`${this.policyBaseUrl}${name}`, { headers }));
  }

  enablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}enable/${name}`, {}, { headers }));
  }

  disablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}disable/${name}`, {}, { headers }));
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
    this._selectedPolicy.set(updatedPolicy);
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
    this._selectedPolicy.set(updatedPolicy);
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
    const scope = this._selectedPolicy()?.scope;
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
      return value.trim().length > 0 && !isNaN(Number(value)) && Number.isInteger(Number(value));
    } else if (actionType === "str") {
      return value.trim().length > 0;
    } else if (actionType === "text") {
      return value.trim().length > 0;
    }
    return false;
  }

  cancelEditMode() {
    const originalPolicy = this.selectedPolicyOriginal();
    if (originalPolicy) {
      this._selectedPolicy.set({ ...originalPolicy });
    }
    this.viewMode.set("view");
  }
}
