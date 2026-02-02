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

export type AdditionalCondition = [
  SectionOptionKey,
  string,
  ComparatorOptionKey,
  string,
  boolean,
  HandleMissingDataOptionKey
];

export type SectionOptionKey =
  | "HTTP Environment"
  | "HTTP Request header"
  | "Request Data"
  | "container"
  | "container_info"
  | "token"
  | "tokeninfo"
  | "userinfo";

export interface SectionOption {
  key: SectionOptionKey;
  label: string;
}

export const SECTION_OPTIONS: SectionOption[] = [
  { key: "HTTP Environment", label: $localize`HTTP Environment` },
  { key: "HTTP Request header", label: $localize`HTTP Request header` },
  { key: "Request Data", label: $localize`Request Data` },
  { key: "container", label: $localize`Container` },
  { key: "container_info", label: $localize`Container Info` },
  { key: "token", label: $localize`Token` },
  { key: "tokeninfo", label: $localize`Token Info` },
  { key: "userinfo", label: $localize`User Info` }
];
// 1. Comparator Options
export type ComparatorOptionKey =
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

export interface ComparatorOption {
  key: ComparatorOptionKey;
  label: string;
}

export const COMPARATOR_OPTIONS: ComparatorOption[] = [
  { key: "contains", label: $localize`Contains` },
  { key: "!contains", label: $localize`Does not contain` },
  { key: "equals", label: $localize`Equals` },
  { key: "!equals", label: $localize`Does not equal` },
  { key: "matches", label: $localize`Matches (Regex)` },
  { key: "!matches", label: $localize`Does not match (Regex)` },
  { key: "in", label: $localize`In` },
  { key: "!in", label: $localize`Not in` },
  { key: "string_contains", label: $localize`String contains` },
  { key: "!string_contains", label: $localize`String does not contain` },
  { key: "date_within_last", label: $localize`Within last...` },
  { key: "!date_within_last", label: $localize`Not within last...` },
  { key: "date_after", label: $localize`Date after` },
  { key: "date_before", label: $localize`Date before` },
  { key: "<", label: $localize`Less than` },
  { key: ">", label: $localize`Greater than` }
];

// 2. Handle Missing Data Options
export type HandleMissingDataOptionKey = "raise_error" | "condition_is_false" | "condition_is_true";

export interface HandleMissingDataOption {
  key: HandleMissingDataOptionKey;
  label: string;
}

export const HANDLE_MISSING_DATA_OPTIONS: HandleMissingDataOption[] = [
  { key: "raise_error", label: "Raise error" },
  { key: "condition_is_false", label: "Condition is false" },
  { key: "condition_is_true", label: "Condition is true" }
];

export interface PolicyServiceInterface {
  getEmptyPolicy(): PolicyDetail;
  readonly isEditMode: Signal<boolean>;
  readonly policyActions: Signal<ScopedPolicyActions>;
  readonly allPolicyActionsFlat: Signal<{ [actionName: string]: PolicyActionDetail }>;
  readonly allPolicyScopes: Signal<string[]>;
  readonly policyActionsByGroup: Signal<PolicyActionGroups>;
  filteredPolicyActionGroups(alreadyAddedActionNames: string[], filterValue: string): PolicyActionGroups;
  getActionDetail(actionName: string, scope: string): PolicyActionDetail | null;
  getGroupOfAction(actionName: string, scope: string): string | null;
  getScopeOfAction(name: string): string | null;
  readonly allPolicies: Signal<PolicyDetail[]>;
  canSavePolicy(policy: PolicyDetail): boolean;
  getDetailsOfAction(actionName: string): PolicyActionDetail | null;
  copyPolicy(policyDetail: PolicyDetail, newName: string): Promise<PiResponse<any>>;
  createPolicy(policyData: PolicyDetail): Promise<PiResponse<any>>;
  updatePolicy(oldPolicyName: String, policyData: PolicyDetail): Promise<PiResponse<any>>;
  deletePolicy(name: string): Promise<PiResponse<number>>;
  enablePolicy(name: string): Promise<PiResponse<any>>;
  disablePolicy(name: string): Promise<PiResponse<any>>;
  isScopeChangeable(policy: PolicyDetail): boolean;
  getActionNamesOf(scope?: string, group?: string): string[];
  getActionsOf(scope?: string, group?: string): Record<string, PolicyActionDetail>;
  actionValueIsValid(action: PolicyActionDetail, value: string | number): boolean;
  saveNewPolicy(newPolicy: PolicyDetail): Promise<void>;
  policyHasConditions(policy: PolicyDetail): boolean;
  policyHasAdminConditions(policy: PolicyDetail): boolean;
  policyHasUserConditions(policy: PolicyDetail): boolean;
  policyHasEnviromentConditions(policy: PolicyDetail): boolean;
  policyHasAdditionalConditions(policy: PolicyDetail): boolean;
  policyHasActions(policy: PolicyDetail): boolean;
  savePolicyEdits(policyName: string, edits: Partial<PolicyDetail>): void;
  isPolicyEdited(editedPolicy: PolicyDetail, originalPolicy: PolicyDetail): boolean;
  togglePolicyActive(policy: PolicyDetail): void;
  updatePolicyOptimistic(updatedPolicy: Partial<PolicyDetail>): void;
  allPoliciesRecource: HttpResourceRef<PiResponse<PolicyDetail[], unknown> | undefined>;
}

@Injectable({
  providedIn: "root"
})
export class PolicyService implements PolicyServiceInterface {
  getScopeOfAction(name: string): string | null {
    const policyActions = this.policyActions();
    for (const scope in policyActions) {
      const actions = policyActions[scope];
      if (actions && actions[name]) {
        return scope;
      }
    }
    return null;
  }
  getGroupOfAction(actionName: string, scope: string): string | null {
    const policyActions = this.policyActions();
    if (policyActions && policyActions[scope]) {
      const actions = policyActions[scope];
      if (actions && actions[actionName]) {
        return actions[actionName].group || null;
      }
    }
    return null;
  }
  readonly isEditMode = linkedSignal({
    source: () => this.contentService.routeUrl(),
    computation: (_) => false
  });
  savePolicyEdits(policyName: string, edits: Partial<PolicyDetail>) {
    // Optimistic update
    const allPolicies = this.allPolicies();
    const backupPolicies = [...allPolicies];
    const index = allPolicies.findIndex((p) => p.name === policyName);
    const originalPolicy = allPolicies[index];
    if (!originalPolicy) {
      console.error("Original policy not found for update");
      return;
    }
    const updatedPolicy = { ...originalPolicy, ...edits };
    allPolicies[index] = updatedPolicy;
    this.allPolicies.set(allPolicies);

    // Do request
    this.http
      .post<PiResponse<any>>(`${this.policyBaseUrl}${policyName}`, updatedPolicy, {
        headers: this.authService.getHeaders()
      })
      .subscribe({
        next: () => {
          // Do request that may revert the optimistic update
          this.allPoliciesRecource.reload();
        },
        error: (err) => {
          // Rollback optimistic update
          this.allPolicies.set(backupPolicies);
          console.error("Error updating policy: ", err);
        }
      });
  }

  private readonly contentService: ContentServiceInterface = inject(ContentService);

  canSavePolicy(policy: PolicyDetail): boolean {
    if (!policy) return false;
    if (!policy.name || policy.name.trim() === "") return false;
    if (!policy.scope || policy.scope.trim() === "") return false;
    if (!this.policyHasActions(policy)) return false;
    return true;
  }

  policyHasActions(policy: PolicyDetail): boolean {
    if (policy?.action && Object.keys(policy.action).length > 0) {
      return true;
    }
    return false;
  }

  policyHasAdminConditions(policy: PolicyDetail): boolean {
    if (policy?.adminrealm && policy.adminrealm.length > 0) return true;
    if (policy?.adminuser && policy.adminuser.length > 0) return true;
    return false;
  }

  policyHasUserConditions(policy: PolicyDetail): boolean {
    if (policy?.realm && policy.realm.length > 0) return true;
    if (policy?.resolver && policy.resolver.length > 0) return true;
    if (policy?.user && policy.user.length > 0) return true;
    return false;
  }

  policyHasEnviromentConditions(policy: PolicyDetail): boolean {
    if (policy?.pinode && policy.pinode.length > 0) return true;
    if (policy?.time && policy.time.length > 0) return true;
    if (policy?.client && policy.client.length > 0) return true;
    if (policy?.user_agents && policy.user_agents.length > 0) return true;
    return false;
  }

  policyHasAdditionalConditions(policy: PolicyDetail): boolean {
    if (policy?.conditions && policy.conditions.length > 0) return true;
    return false;
  }

  policyHasConditions(policy: PolicyDetail): boolean {
    if (this.policyHasAdminConditions(policy)) return true;
    if (this.policyHasUserConditions(policy)) return true;
    if (this.policyHasEnviromentConditions(policy)) return true;
    if (this.policyHasAdditionalConditions(policy)) return true;
    return false;
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

    return promise;
  }

  getDetailsOfAction(actionName: string): PolicyActionDetail | null {
    const actions = this.allPolicyActionsFlat();
    if (actionName && actions) {
      return actions[actionName] ?? null;
    }
    return null;
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

  filteredPolicyActionGroups(alreadyAddedActionNames: string[], filterValue: string): PolicyActionGroups {
    // Also filter out already added actions
    if (!filterValue && alreadyAddedActionNames.length === 0) {
      return this.policyActionsByGroup();
    }
    const policyActions = this.policyActionResource.value()?.result?.value;
    if (!policyActions) return {};
    const grouped: PolicyActionGroups = {};
    filterValue = filterValue.toLowerCase();
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
  }

  /**
   * Filter policy actions by the actionFilter signal and already added actions.
   * @returns {PolicyActionGroups} The filtered policy actions grouped by scope and group.
   */
  // currentActionGroupsFiltered = computed<PolicyActionGroups>(() => {
  //   return this.filteredPolicyActionGroups(this.alreadyAddedActionNames(), this.actionFilter());
  // });

  _allPolicies = computed(() => this.allPoliciesRecource.value()?.result?.value ?? []);

  allPolicies = linkedSignal({
    source: () => this._allPolicies(),
    computation: (source) => {
      return source.sort((a, b) => a.priority - b.priority);
    }
  });

  filteredGroupNamesOf(selectedScope: string, alreadyAddedActionNames: string[], filter: string): string[] {
    const policyActionGroupFiltered = this.filteredPolicyActionGroups(alreadyAddedActionNames, filter)[selectedScope];
    if (!policyActionGroupFiltered) return [];
    return Object.keys(policyActionGroupFiltered);
  }

  getActionDetail = (actionName: string, scope: string): PolicyActionDetail | null => {
    const actions = this.policyActions();

    if (actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  };

  getActionNamesOf(scope?: string, group?: string): string[] {
    const actions = this.policyActions();
    console.log("getActionNamesOf", scope, group);
    if (!actions) return [];
    if (scope) {
      if (group) {
        const actionsInGroup = Object.entries(actions[scope] || {}).filter(
          ([, actionDetail]) => actionDetail.group === group
        );
        return actionsInGroup.map(([actionName]) => actionName);
      } else {
        return Object.keys(actions[scope] || {});
      }
    } else {
      return Object.keys(this.allPolicyActionsFlat());
    }
  }

  getActionsOf(scope?: string, group?: string): Record<string, PolicyActionDetail> {
    const actions = this.policyActions();
    const result: Record<string, PolicyActionDetail> = {};
    if (!actions) return result;
    if (scope) {
      if (group) {
        let actionsInGroup: [string, PolicyActionDetail][];
        if (group === "Other") {
          actionsInGroup = Object.entries(actions[scope] || {}).filter(([, actionDetail]) => !actionDetail.group);
        } else {
          actionsInGroup = Object.entries(actions[scope] || {}).filter(
            ([, actionDetail]) => actionDetail.group === group
          );
        }

        for (const [actionName, actionDetail] of actionsInGroup) {
          result[actionName] = actionDetail;
        }
      } else {
        const actionsInScope = Object.entries(actions[scope] || {});
        for (const [actionName, actionDetail] of actionsInScope) {
          result[actionName] = actionDetail;
        }
      }
    } else {
      const allActions = this.allPolicyActionsFlat();
      for (const actionName in allActions) {
        result[actionName] = allActions[actionName];
      }
    }
    return result;
  }

  copyPolicy(policyData: PolicyDetail, newName: string): Promise<PiResponse<any>> {
    const copiedPolicy: PolicyDetail = { ...policyData, name: String(newName) };
    return this.createPolicy(copiedPolicy);
  }

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

  async deletePolicy(name: string): Promise<PiResponse<number>> {
    const allPolicies = this.allPolicies();
    if (!allPolicies) return Promise.reject("No policies found");
    const policy = allPolicies.find((p) => p.name === name);
    if (!policy) return Promise.reject(`Policy with name ${name} not found`);

    // Optimistic update
    const updatedPolicies = allPolicies.filter((p) => p.name !== name);
    this.allPolicies.set(updatedPolicies);

    // Do request
    const headers = this.authService.getHeaders();
    const result = await lastValueFrom(
      this.http.delete<PiResponse<number>>(`${this.policyBaseUrl}${name}`, { headers })
    );
    // Reload policies to ensure state is correct
    if (result && !result.result?.error) {
      this.allPoliciesRecource.reload();
    } else {
      // Rollback optimistic update
      this.allPolicies.set(allPolicies);
    }
    return result;
  }
  togglePolicyActive(policy: PolicyDetail): void {
    const action = policy.active ? this.disablePolicy(policy.name) : this.enablePolicy(policy.name);
    // Optimistic update
    const currentPolicies = this.allPolicies();
    this.allPolicies.set(currentPolicies.map((p) => (p.name === policy.name ? { ...p, active: !policy.active } : p)));
    // Do request
    action.catch((error) => {
      // Rollback optimistic update
      this.allPolicies.set(currentPolicies);
      console.error("Error toggling policy active state: ", error);
    });
    // Reload policies to ensure state is correct (in case other properties changed)
    action.then(() => {
      this.allPoliciesRecource.reload();
    });
  }
  enablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}enable/${name}`, {}, { headers }));
  }

  disablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}disable/${name}`, {}, { headers }));
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

  updatePolicyOptimistic(updatedPolicy: PolicyDetail) {
    const currentPolicies = this.allPolicies();
    this.allPolicies.set(currentPolicies.map((p) => (p.name === updatedPolicy.name ? updatedPolicy : p)));
    this.http.post("/api/policy", updatedPolicy).subscribe({
      error: (err) => {
        this.allPolicies.set(currentPolicies);
        console.error("Update failed, rolling back", err);
      }
    });
  }
}
