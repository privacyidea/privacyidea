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
import { computed, effect, inject, Injectable, linkedSignal, Signal } from "@angular/core";
import { lastValueFrom } from "rxjs";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";

export type ActionType = "bool" | "int" | "str" | "text";
export type PolicyActionDetail<T extends string | number = string | number> = {
  desc: string;
  type: ActionType;
  multiple?: boolean;
  group?: string;
  mainmenu?: string[];
  value?: T[];
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
  action: { [actionName: string]: string | boolean } | null;
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
  { key: "raise_error", label: $localize`Raise error` },
  { key: "condition_is_false", label: $localize`Condition is false` },
  { key: "condition_is_true", label: $localize`Condition is true` }
];

export interface PolicyServiceInterface {
  readonly isEditMode: Signal<boolean>;
  readonly policyActions: Signal<ScopedPolicyActions>;
  readonly allPolicyActionsFlat: Signal<{ [actionName: string]: PolicyActionDetail }>;
  readonly allPolicyScopes: Signal<string[]>;
  readonly policyActionsByGroup: Signal<PolicyActionGroups>;
  readonly allPolicies: Signal<PolicyDetail[]>;
  allPoliciesResource: HttpResourceRef<PiResponse<PolicyDetail[], unknown> | undefined>;
  policyActionResource: HttpResourceRef<PiResponse<ScopedPolicyActions> | undefined>;

  getEmptyPolicy(): PolicyDetail;

  filteredPolicyActionGroups(alreadyAddedActionNames: string[], filterValue: string): PolicyActionGroups;

  getActionDetail(actionName: string, scope: string): PolicyActionDetail | null;

  getGroupOfAction(actionName: string, scope: string): string | null;

  getScopeOfAction(name: string): string | null;

  canSavePolicy(policy: PolicyDetail): boolean;

  getDetailsOfAction(actionName: string): PolicyActionDetail | null;

  copyPolicy(oldName: string, newName: string): Promise<PiResponse<any>>;

  createPolicy(policyData: PolicyDetail): Promise<PiResponse<any>>;

  deletePolicy(name: string): Promise<PiResponse<number>>;

  enablePolicy(name: string): Promise<PiResponse<any>>;

  disablePolicy(name: string): Promise<PiResponse<any>>;

  isScopeChangeable(policy: PolicyDetail): boolean;

  getActionNamesOf(scope?: string, group?: string): string[];

  getActionsOf(scope?: string, group?: string): Record<string, PolicyActionDetail>;

  actionValueIsValid(action: PolicyActionDetail, value: string | number): boolean;

  saveNewPolicy(newPolicy: PolicyDetail): Promise<boolean>;

  policyHasConditions(policy: PolicyDetail): boolean;

  policyHasAdminConditions(policy: PolicyDetail): boolean;

  policyHasUserConditions(policy: PolicyDetail): boolean;

  policyHasEnvironmentConditions(policy: PolicyDetail): boolean;

  policyHasAdditionalConditions(policy: PolicyDetail): boolean;

  policyHasActions(policy: PolicyDetail): boolean;

  isPolicyEdited(editedPolicy: PolicyDetail, originalPolicy: PolicyDetail): boolean;

  togglePolicyActive(policy: PolicyDetail): void;

  savePolicyEdits(originalPolicyName: string, updatedPolicy: PolicyDetail): Promise<boolean>;
}

@Injectable({
  providedIn: "root"
})
export class PolicyService implements PolicyServiceInterface {
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly policyBaseUrl = environment.proxyUrl + "/policy/";
  private readonly http: HttpClient = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.allPoliciesResource.error(), "policies");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.policyActionResource.error(), "policy actions");
    });
  }
  readonly policyActionResource = httpResource<PiResponse<ScopedPolicyActions>>(() => {
    // Only load policy definitions on the policies route.
    if (!this.contentService.onPolicies()) {
      return undefined;
    }

    return {
      url: `${this.policyBaseUrl}defs`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  /**
   * Filter policy actions by the actionFilter signal and already added actions.
   * @returns {PolicyActionGroups} The filtered policy actions grouped by scope and group.
   */
    // currentActionGroupsFiltered = computed<PolicyActionGroups>(() => {
    //   return this.filteredPolicyActionGroups(this.alreadyAddedActionNames(), this.actionFilter());
    // });

  _allPolicies = computed(() => {
    if (!this.allPoliciesResource.hasValue()) return [];
    return this.allPoliciesResource.value()?.result?.value ?? []
  });

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

  readonly isEditMode = linkedSignal({
    source: () => this.contentService.routeUrl(),
    computation: (_) => false
  });
  policyActions = computed(() => {
    if (!this.policyActionResource.hasValue()) return {};
    return this.policyActionResource.value()?.result?.value ?? {};
  });
  allPolicyActionsFlat = computed(() => {
    const policyActions = this.policyActions();
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
    const policyActions = this.policyActions();
    return Object.keys(policyActions);
  });
  policyActionsByGroup = computed<PolicyActionGroups>(() => {
    const policyActions = this.policyActions();
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
    if (!this.policyActionResource.hasValue()) return {};
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

  getActionDetail = (actionName: string, scope: string): PolicyActionDetail | null => {
    const actions = this.policyActions();

    if (actions && actions[scope]) {
      return actions[scope][actionName] ?? null;
    }
    return null;
  };

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

  allPolicies = linkedSignal({
    source: () => this._allPolicies(),
    computation: (source) => {
      return source.sort((a, b) => a.priority - b.priority);
    }
  });

  canSavePolicy(policy: PolicyDetail): boolean {
    if (!policy) return false;
    if (!policy.name || policy.name.trim() === "") return false;
    if (!policy.scope || policy.scope.trim() === "") return false;
    if (!this.policyHasActions(policy)) return false;
    return true;
  }

  getDetailsOfAction(actionName: string): PolicyActionDetail | null {
    const actions = this.allPolicyActionsFlat();
    if (actionName && actions) {
      return actions[actionName] ?? null;
    }
    return null;
  }

  copyPolicy(oldName: string, newName: string): Promise<PiResponse<any>> {
    const policyData = this.allPolicies().find((p) => p.name === oldName);
    if (!policyData) return Promise.reject("Policy not found");
    const copiedPolicy: PolicyDetail = { ...policyData, name: String(newName) };
    return this.createPolicy(copiedPolicy);
  }

  // -----------------------------------
  // 2.3 Computed Signals (Derived State)
  // -----------------------------------

  createPolicy(policyData: PolicyDetail): Promise<PiResponse<any>> {
    const allPoliciesCopy = [...this.allPolicies()];
    allPoliciesCopy.push({ ...policyData });
    this.allPolicies.set(allPoliciesCopy);

    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post<PiResponse<any>>(`${this.policyBaseUrl}${policyData.name}`, policyData, { headers })
    );
  }

  async deletePolicy(name: string): Promise<PiResponse<number>> {
    const allPolicies = this.allPolicies();
    if (!allPolicies) return Promise.reject("No policies found");
    const policy = allPolicies.find((p) => p.name === name);
    if (!policy) return Promise.reject(`Policy with name ${name} not found`);

    // Optimistic update
    const updatedPolicies = allPolicies.filter((p) => p.name !== name);
    this.allPolicies.set(updatedPolicies);

    try {
      // Do request
      const headers = this.authService.getHeaders();
      const result = await lastValueFrom(
        this.http.delete<PiResponse<number>>(`${this.policyBaseUrl}${name}`, { headers })
      );
      // Reload policies to ensure state is correct
      if (result && !result.result?.error) {
        this.allPoliciesResource.reload();
      } else {
        // Rollback optimistic update
        this.allPolicies.set(allPolicies);
      }
      return result;
    } catch (error: any) {
      // Rollback optimistic update
      this.allPolicies.set(allPolicies);
      const errorMessage = error?.error?.result?.error?.message || "";
      this.notificationService.openSnackBar($localize`Failed to delete policy. ` + errorMessage);
      throw error;
    }
  }

  enablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post<PiResponse<any>>(`${this.policyBaseUrl}enable/${name}`, {}, { headers })).catch(
      (error: any) => {
        const errorMessage = error?.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Failed to enable policy. ` + errorMessage);
        throw error;
      }
    );
  }

  disablePolicy(name: string): Promise<PiResponse<any>> {
    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post<PiResponse<any>>(`${this.policyBaseUrl}disable/${name}`, {}, { headers })
    ).catch((error: any) => {
      const errorMessage = error?.error?.result?.error?.message || "";
      this.notificationService.openSnackBar($localize`Failed to disable policy. ` + errorMessage);
      throw error;
    });
  }

  isScopeChangeable(policy: PolicyDetail): boolean {
    if (!policy.action) return true;
    return Object.keys(policy.action).length === 0;
  }

  getActionNamesOf(scope?: string, group?: string): string[] {
    const actions = this.policyActions();
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

  async saveNewPolicy(newPolicy: PolicyDetail): Promise<boolean> {
    return this.createPolicy(newPolicy)
      .then((response) => {
        this.allPoliciesResource.reload();
        if (response && response.result?.status) {
          this.notificationService.openSnackBar($localize`Policy created successfully.`);
          return true;
        } else {
          const error = response.result?.error?.message || "";
          this.notificationService.openSnackBar($localize`Creating policy failed: ${error}`);
          return false;
        }
      })
      .catch((error) => {
        console.error("Error creating policy: ", error);
        const errorMessage = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar($localize`Creating policy failed: ${errorMessage}`);
        this.allPoliciesResource.reload();
        return false;
      });
  }

  policyHasConditions(policy: PolicyDetail): boolean {
    if (this.policyHasAdminConditions(policy)) return true;
    if (this.policyHasUserConditions(policy)) return true;
    if (this.policyHasEnvironmentConditions(policy)) return true;
    if (this.policyHasAdditionalConditions(policy)) return true;
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

  policyHasEnvironmentConditions(policy: PolicyDetail): boolean {
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

  policyHasActions(policy: PolicyDetail): boolean {
    if (policy?.action && Object.keys(policy.action).length > 0) {
      return true;
    }
    return false;
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

  togglePolicyActive(policy: PolicyDetail): void {
    const action = policy.active ? this.disablePolicy(policy.name) : this.enablePolicy(policy.name);
    // Optimistic update
    const currentPolicies = this.allPolicies();
    this.allPolicies.set(currentPolicies.map((p) => (p.name === policy.name ? { ...p, active: !policy.active } : p)));
    // Do request
    action.catch((error) => {
      // Rollback optimistic update
      this.allPolicies.set(currentPolicies);
      // Error notification already handled in enablePolicy/disablePolicy
      console.error("Error toggling policy active state: ", error);
    });
    // Reload policies to ensure state is correct (in case other properties changed)
    action.then(() => {
      this.allPoliciesResource.reload();
    });
  }

  async savePolicyEdits(originalPolicyName: string, updatedPolicy: PolicyDetail): Promise<boolean> {
    let lastStableState = [...this.allPolicies()];
    const headers = this.authService.getHeaders();
    const hasNameChange = updatedPolicy.name && updatedPolicy.name !== originalPolicyName;

    this.allPolicies.set(lastStableState.map((p) => (p.name === originalPolicyName ? { ...p, ...updatedPolicy } : p)));

    try {
      await lastValueFrom(this.http.post(`${this.policyBaseUrl}${originalPolicyName}`, updatedPolicy, { headers }));

      lastStableState = lastStableState.map((p) =>
        p.name === originalPolicyName ? { ...p, ...updatedPolicy, name: originalPolicyName } : p
      );

      if (hasNameChange) {
        await lastValueFrom(
          this.http.patch(`${this.policyBaseUrl}${originalPolicyName}`, { name: updatedPolicy.name }, { headers })
        );
      }

      this.allPoliciesResource.reload();
      this.notificationService.openSnackBar($localize`Policy updated successfully`);
      return true;
    } catch (error: any) {
      this.allPolicies.set(lastStableState);
      let errorMessage = error?.error?.result?.error?.message || "";
      errorMessage = errorMessage ? `: ${errorMessage}` : "";
      this.notificationService.openSnackBar($localize`Saving policy failed` + errorMessage);
      return false;
    }
  }

  readonly allPoliciesResource = httpResource<PiResponse<PolicyDetail[]>>(() => {
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

  filteredGroupNamesOf(selectedScope: string, alreadyAddedActionNames: string[], filter: string): string[] {
    const policyActionGroupFiltered = this.filteredPolicyActionGroups(alreadyAddedActionNames, filter)[selectedScope];
    if (!policyActionGroupFiltered) return [];
    return Object.keys(policyActionGroupFiltered);
  }
}
