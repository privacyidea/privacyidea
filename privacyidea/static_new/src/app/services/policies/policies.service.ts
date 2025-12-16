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
import { lastValueFrom, Observable, of, switchMap } from "rxjs";
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

export type AdditionalCondition = [SectionOption, string, ComporatorOption, string, boolean, HandleMissingDataOption];

export type SectionOption =
  | "HTTP Environment"
  | "HTTP Request header"
  | "Request Data"
  | "container"
  | "container_info"
  | "token"
  | "tokeninfo"
  | "userinfo";

export const allSectionOptions: SectionOption[] = [
  "HTTP Environment",
  "HTTP Request header",
  "Request Data",
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

export type HandleMissingDataOption = "raise_error" | "condition_is_false" | "condition_is_true";

export const allHandleMissingDataOptions: HandleMissingDataOption[] = [
  "raise_error",
  "condition_is_false",
  "condition_is_true"
];

export interface PolicyServiceInterface {
  getEmptyPolicy(): PolicyDetail;

  readonly isEditMode: Signal<boolean>;
  readonly selectedPolicyHasActions: Signal<boolean>;
  readonly selectedPolicyHasUserConditions: Signal<boolean>;
  readonly selectedPolicyHasNodeConditions: Signal<boolean>;
  readonly selectedPolicyHasAdditionalConditions: Signal<boolean>;
  readonly selectedPolicyHasConditions: Signal<boolean>;
  readonly isSelectedPolicyEdited: Signal<boolean>;
  readonly selectedPolicy: Signal<PolicyDetail | null>;
  readonly selectedPolicyOriginal: Signal<PolicyDetail | null>;
  readonly actionFilter: WritableSignal<string>;
  readonly policyActionGroupNames: Signal<string[]>;
  readonly selectedActionGroup: WritableSignal<string>;
  readonly selectedAction: WritableSignal<{ name: string; value: any } | null>;
  readonly policyActions: Signal<ScopedPolicyActions>;
  readonly allPolicyActionsFlat: Signal<{ [actionName: string]: PolicyActionDetail }>;
  readonly allPolicyScopes: Signal<string[]>;
  readonly policyActionsByGroup: Signal<PolicyActionGroups>;
  readonly alreadyAddedActionNames: Signal<string[]>;
  readonly policyActionsByGroupFiltered: Signal<PolicyActionGroups>;
  readonly allPolicies: Signal<PolicyDetail[]>;
  readonly selectedPolicyScope: Signal<string>;
  readonly selectedActionDetail: Signal<PolicyActionDetail | null>;

  updateActionInSelectedPolicy(): void;
  updateActionValue(actionName: string, newValue: boolean): void;
  selectPolicyByName(policyName: string): void;
  canSavePolicy(policy: PolicyDetail): boolean;
  savePolicyEdits(args?: { asNew?: boolean }): Promise<void> | undefined;
  getDetailsOfAction(actionName: string): PolicyActionDetail | null;
  deselectNewPolicy(): void;
  deselectPolicy(name: string): void;
  initializeNewPolicy(): void;
  selectPolicy(policy: PolicyDetail): void;
  updateSelectedPolicy(args: Partial<PolicyDetail>): void;
  selectActionByName(actionName: string): void;
  updateSelectedActionValue(value: any): void;
  createPolicy(policyData: PolicyDetail): Promise<PiResponse<any>>;
  updatePolicy(oldPolicyName: String, policyData: PolicyDetail): Promise<PiResponse<any>>;
  deletePolicy(name: string): Promise<PiResponse<number>>;
  enablePolicy(name: string): Promise<PiResponse<any>>;
  disablePolicy(name: string): Promise<PiResponse<any>>;
  addActionToSelectedPolicy(): void;
  removeActionFromSelectedPolicy(actionName: string): void;
  isScopeChangeable(policy: PolicyDetail): boolean;
  actionNamesOfSelectedGroup(): string[];
  actionValueIsValid(action: PolicyActionDetail, value: string | number): boolean;
  cancelEditMode(): void;
}

@Injectable({
  providedIn: "root"
})
export class PolicyService implements PolicyServiceInterface {
  readonly isEditMode = linkedSignal({
    source: () => this.contentService.routeUrl(),
    computation: (_) => false
  });

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

  selectPolicyByName(policyName: string) {
    const policy = this.allPolicies().find((p) => p.name === policyName);
    if (policy) {
      this.selectPolicy(policy);
    }
  }

  canSavePolicy(policy: PolicyDetail): boolean {
    if (!policy) return false;
    if (!policy.name || policy.name.trim() === "") return false;
    if (!policy.scope || policy.scope.trim() === "") return false;
    if (!this.selectedPolicyHasActions()) return false;
    return true;
  }

  policyHasActions(policy: PolicyDetail): boolean {
    if (policy?.action && Object.keys(policy.action).length > 0) {
      return true;
    }
    return false;
  }

  readonly selectedPolicyHasActions = computed<boolean>(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return this.policyHasActions(policy);
  });

  policyHasAdminConditions(policy: PolicyDetail): boolean {
    if (policy?.adminrealm && policy.adminrealm.length > 0) return true;
    if (policy?.adminuser && policy.adminuser.length > 0) return true;
    return false;
  }

  readonly selectedPolicyHasAdminConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return this.policyHasAdminConditions(policy);
  });

  policyHasUserConditions(policy: PolicyDetail): boolean {
    if (policy?.realm && policy.realm.length > 0) return true;
    if (policy?.resolver && policy.resolver.length > 0) return true;
    if (policy?.user && policy.user.length > 0) return true;
    return false;
  }

  readonly selectedPolicyHasUserConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return this.policyHasUserConditions(policy);
  });

  policyHasNodeConditions(policy: PolicyDetail): boolean {
    if (policy?.pinode && policy.pinode.length > 0) return true;
    if (policy?.time && policy.time.length > 0) return true;
    if (policy?.client && policy.client.length > 0) return true;
    if (policy?.user_agents && policy.user_agents.length > 0) return true;
    return false;
  }

  readonly selectedPolicyHasNodeConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return this.policyHasNodeConditions(policy);
  });

  policyHasAdditionalConditions(policy: PolicyDetail): boolean {
    if (policy?.conditions && policy.conditions.length > 0) return true;
    return false;
  }

  readonly selectedPolicyHasAdditionalConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return this.policyHasAdditionalConditions(policy);
  });

  policyHasConditions(policy: PolicyDetail): boolean {
    if (this.policyHasAdminConditions(policy)) return true;
    if (this.policyHasUserConditions(policy)) return true;
    if (this.policyHasNodeConditions(policy)) return true;
    if (this.policyHasAdditionalConditions(policy)) return true;
    return false;
  }

  readonly selectedPolicyHasConditions = computed(() => {
    const policy = this.selectedPolicy();
    if (!policy) return false;
    return this.policyHasConditions(policy);
  });

  savePolicyEdits(): Promise<void> | undefined {
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

    const promise = this.updatePolicy(oldPolicyName, selectedPolicy)
      .then((_) => {
        this.allPoliciesRecource.reload();
      })
      .catch((error) => {
        console.error("Error updating policy: ", error);
      });

    this.selectPolicy(selectedPolicy);
    return promise;
  }

  saveNewPolicy(newPolicy: PolicyDetail): Promise<void> {
    const allPoliciesCopy = this.allPolicies();
    allPoliciesCopy.push({ ...newPolicy });
    this.allPolicies.set(allPoliciesCopy);

    const promise = this.createPolicy(newPolicy)
      .then((_) => {
        this.allPoliciesRecource.reload();
      })
      .catch((error) => {
        console.error("Error creating policy: ", error);
        return Promise.reject();
      });

    this.selectPolicy(newPolicy);
    return promise;
  }

  getDetailsOfAction(actionName: string): PolicyActionDetail | null {
    const actions = this.allPolicyActionsFlat();
    if (actionName && actions) {
      return actions[actionName] ?? null;
    }
    return null;
  }

  deselectNewPolicy() {
    this.deselectPolicy(this.getEmptyPolicy().name);
  }

  deselectPolicy(name: string) {
    if (this.selectedPolicyOriginal()?.name !== name) return;
    this._selectedPolicy.set(null);
    this._selectedPolicyOriginal.set(null);
  }

  getEmptyPolicy(): PolicyDetail {
    return {
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
  }

  initializeNewPolicy() {
    this._selectedPolicy.set({ ...this.getEmptyPolicy() });
    this._selectedPolicyOriginal.set({ ...this.getEmptyPolicy() });
  }

  isPolicyEdited(editedPolicy: PolicyDetail, originalPolicy: PolicyDetail): boolean {
    if (JSON.stringify(originalPolicy) === JSON.stringify(this.getEmptyPolicy())) {
      // remove scope temporarily and then compare to ignore scope changes
      const { scope: _, ...selectedWithoutScope } = editedPolicy;
      const { scope: __, ...originalWithoutScope } = originalPolicy;
      return JSON.stringify(selectedWithoutScope) !== JSON.stringify(originalWithoutScope);
    } else {
      return JSON.stringify(editedPolicy) !== JSON.stringify(originalPolicy);
    }
  }
  readonly isSelectedPolicyEdited = computed(() => {
    const selectedPolicy = this.selectedPolicy();
    const originalPolicy = this.selectedPolicyOriginal();
    if (!selectedPolicy || !originalPolicy) return false;
    return this.isPolicyEdited(selectedPolicy, originalPolicy);
  });

  selectPolicy(policy: PolicyDetail) {
    this._selectedPolicy.set(policy);
    this._selectedPolicyOriginal.set({ ...policy });
  }

  updateSelectedPolicy(args: Partial<PolicyDetail>) {
    const selectedPolicy = this.selectedPolicy();
    if (!selectedPolicy) return;
    const updatedPolicy = {
      ...selectedPolicy,
      ...args
    };
    this._selectedPolicy.set(updatedPolicy);
  }

  readonly policyBaseUrl = environment.proxyUrl + "/policy/";

  private readonly http: HttpClient = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  readonly policyActionResource = httpResource<PiResponse<ScopedPolicyActions>>(() => ({
    url: `${this.policyBaseUrl}defs`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  readonly allPoliciesRecource = httpResource<PiResponse<PolicyDetail[]>>(() => {
    // Only load policies if the action is allowed.
    if (!this.authService.actionAllowed("policyread")) {
      return undefined;
    }
    // Only load policies on policies route.
    if (!this.contentService.onPolicies()) {
      return undefined;
    }
    return {
      url: `${this.policyBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  private readonly _selectedPolicy = signal<PolicyDetail | null>(null);
  readonly selectedPolicy = computed(() => this._selectedPolicy());

  private _selectedPolicyOriginal = signal<PolicyDetail | null>(null);
  selectedPolicyOriginal = computed(() => this._selectedPolicyOriginal());

  actionFilter = linkedSignal({
    source: () => {
      this._selectedPolicyOriginal();
    },
    computation: (_) => ""
  });

  selectedActionGroup: WritableSignal<string> = linkedSignal({
    source: () => this.policyActionGroupNames(),
    computation: (source, previous) => {
      if (source.length < 1) return "";
      if (previous && source.includes(previous.value)) return previous.value;
      return source[0];
    }
  });

  selectedAction: WritableSignal<{ name: string; value: any } | null> = linkedSignal({
    source: () => ({
      actionNamesOfSelectedGroup: this.actionNamesOfSelectedGroup() ?? [],
      _selectedPolicy: this._selectedPolicy(),
      isEditMode: this.isEditMode()
    }),
    computation: (source, previous) => {
      const { actionNamesOfSelectedGroup, _selectedPolicy } = source;
      if (previous?.value && _selectedPolicy?.action?.[previous.value.name]) {
        return previous.value;
      }
      if (this.isEditMode()) {
        const previousValue = previous?.value;
        if (actionNamesOfSelectedGroup.length < 1) return null;
        if (previousValue && actionNamesOfSelectedGroup.includes(previousValue.name)) return previous.value;
        const firstActionName = actionNamesOfSelectedGroup[0];
        const defaultValue = this._getActionDetail(firstActionName)?.type === "bool" ? "true" : "";
        return { name: firstActionName, value: defaultValue };
      } else {
        if (_selectedPolicy && _selectedPolicy.action) {
          const actionNames = Object.keys(_selectedPolicy.action);
          if (actionNames.length > 0) {
            const firstActionName = actionNames[0];
            const actionValue = _selectedPolicy.action[firstActionName];
            return { name: firstActionName, value: actionValue };
          }
        }
        return null;
      }
    }
  });

  selectActionByName(actionName: string) {
    const actionNames = this.actionNamesOfSelectedGroup();
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

  /**
   * Filter policy actions by the actionFilter signal and already added actions.
   * @returns {PolicyActionGroups} The filtered policy actions grouped by scope and group.
   */
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

  selectedPolicyScope = linkedSignal(() => {
    return this._selectedPolicy()?.scope || "";
  });

  policyActionGroupNames: Signal<string[]> = computed(() => {
    const selectedScope = this.selectedPolicyScope();
    console.log("selectedScope:", selectedScope);
    if (!selectedScope) return [];
    const policyActionGroupFiltered = this.policyActionsByGroupFiltered()[selectedScope];
    console.log("policyActionGroupFiltered:", policyActionGroupFiltered);
    if (!policyActionGroupFiltered) return [];
    console.log("Object.keys(policyActionGroupFiltered):", Object.keys(policyActionGroupFiltered));
    return Object.keys(policyActionGroupFiltered);
  });

  _getActionDetail = (actionName: string): PolicyActionDetail | null => {
    const actions = this.policyActions();
    const scope = this.selectedPolicyScope();
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

  actionNamesOfSelectedGroup = computed<string[]>(() => {
    const group: string = this.selectedActionGroup();
    const actionsByGroup = this.policyActionsByGroupFiltered();
    const scope = this.selectedPolicyScope();
    console.log("actionNamesOfSelectedGroup - scope:", scope, "group:", group);
    if (!scope || !actionsByGroup[scope]) return [];
    console.log("returning: ", Object.keys(actionsByGroup[scope][group] || {}));
    return Object.keys(actionsByGroup[scope][group] || {});
  });

  createPolicy(policyData: PolicyDetail): Promise<PiResponse<any>> {
    const allPoliciesCopy = [...this.allPolicies()];
    allPoliciesCopy.push({ ...policyData });
    this.allPolicies.set(allPoliciesCopy);

    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post<PiResponse<any>>(`${this.policyBaseUrl}${policyData.name}`, policyData, { headers })
    );
  }

  updatePolicy(oldPolicyName: string, policyData: PolicyDetail): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    const patch$: Observable<PiResponse<any>> = this.http.patch<PiResponse<any>>(
      `${this.policyBaseUrl}${oldPolicyName}`,
      { name: policyData.name },
      { headers }
    );
    let request$: Observable<PiResponse<any>>;
    if (oldPolicyName !== policyData.name) {
      request$ = patch$.pipe(
        switchMap((patchResponse) => {
          if (patchResponse && patchResponse.result?.error) {
            return of(patchResponse);
          }
          return this.http.post<PiResponse<any>>(`${this.policyBaseUrl}${policyData.name}`, policyData, { headers });
        })
      );
    } else {
      request$ = this.http.post<PiResponse<any>>(`${this.policyBaseUrl}${policyData.name}`, policyData, { headers });
    }
    return lastValueFrom(request$);
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

  isScopeChangeable(policy: PolicyDetail): boolean {
    if (!policy.action) return true;
    return Object.keys(policy.action).length === 0;
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
  }
}
