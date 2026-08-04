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

import { HttpClient, HttpErrorResponse, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, Signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { lastValueFrom } from "rxjs";

// The set of event/action types the UI offers is fetched from the backend at runtime (see
// eventTypesResource / actionTypesResource) so a newly added type shows up without a WebUI change.
// These string-literal unions stay as a compile-time safety net for the per-type UI logic (e.g. the
// ACTION_DESCRIPTIONS record and the value-mode handling keyed by action type): the value strings
// mirror privacyidea.lib.conditional_access.authentication_event_types.AuthEventType and
// privacyidea.lib.conditional_access.engine.LockoutAction.
export type AuthEventType =
  | "NOT_AUTHORIZED"
  | "PASSWORD_FAIL"
  | "PIN_FAIL"
  | "TOKEN_ONLY_FAIL"
  | "MFA_FAIL"
  | "USER_UNKNOWN"
  | "NO_TOKEN"
  | "NO_USABLE_TOKEN"
  | "LOGIN_SUCCESS"
  | "CHALLENGE_CONTINUED"
  | "CHALLENGE_TRIGGERED"
  | "CHALLENGE_ANSWERED_OUT_OF_BAND"
  | "CHALLENGE_ANSWERED_FAIL"
  | "CHALLENGE_DECLINED"
  | "ENROLLMENT_TRIGGERED"
  | "ENROLLMENT_CANCELED_FAIL"
  | "UNKNOWN_FAIL_REASON";

export type LockoutActionType =
  | "LOCK_USER"
  | "PERMANENT_LOCK_USER"
  | "EMAIL_ADMIN"
  | "EMAIL_USER"
  | "BLOCK_IP"
  | "PERMANENT_BLOCK_IP"
  | "ALLOW"
  | "DENY";

// The identity a policy counts and acts on.
export type LockoutTarget = "user" | "source_ip";

// How the tracked counters are counted against the stage thresholds; which values are valid depends on the
// target (see the /conditionalaccess/targets endpoint). Mirrors
// privacyidea.lib.conditional_access.authentication_event_types.CountMode.
export type CountMode = "PER_REQUEST" | "PER_ATTEMPT" | "DISTINCT_USERS";

// Everything the backend constrains by target, served per target by /conditionalaccess/targets: the stage actions
// it allows and the count modes it supports (both sorted; the UI treats the first count mode as the default).
export interface TargetConstraints {
  actions: LockoutActionType[];
  count_modes: CountMode[];
}

export interface LockoutStageAction {
  id?: number;
  action_type: LockoutActionType;
  action_value: unknown;
  // When false (default) the action fires once, at its stage's exact threshold;
  // when true it keeps firing while the count stays at or above the threshold.
  retrigger_above_threshold?: boolean;
}

export interface LockoutPolicyStage {
  id?: number;
  name?: string | null;
  failure_threshold: number;
  priority: number;
  actions: LockoutStageAction[];
}

// The condition types and operators this WebUI ships hand-written wording for (mirroring
// ConditionType / ConditionOperator in privacyidea.lib.conditional_access.conditions).
//
// These are deliberately NOT the type of any value read off the wire: that registry is open by design
// ("adding a condition kind is a registry entry, not a schema change"), the editor builds its rows
// from /conditiontypes, and a served value outside these unions is a case the UI handles rather than a
// type error. condition_type and operator are therefore plain strings below.
//
// What they are for is the reverse direction - locking the *client's* own tables to the vocabulary it
// claims to support. KnownConditionOperator keyed over a full (non-Partial) Record is what makes
// "every operator rendered with bespoke copy has that copy" a compile-time rule; KnownConditionType
// keys the copy table so a mistyped key is caught rather than silently never matching.
export type KnownConditionType = "USER_REALM" | "USER_ROLE";
export type KnownConditionOperator = "IN" | "NOT_IN";

// One comparison a condition type permits, with the label the backend has already translated.
export interface ConditionOperatorMeta {
  name: string;
  label: string;
}

// What /conditionalaccess/conditiontypes serves per condition type: its translated label, the
// operators it permits and the values that are valid *right now* (null for a type whose values cannot
// be enumerated). "choices" is resolved server-side per request, so a realm deleted since the last
// load shows up as unknown rather than silently staying selectable.
export interface ConditionTypeMeta {
  label: string;
  operators: ConditionOperatorMeta[];
  choices: string[] | null;
}

// One restriction on which requests a policy applies to. All of a policy's conditions must hold
// (AND); a policy with no conditions applies to every request. The backend rejects an empty "value"
// list, so "no restriction on this type" is expressed by omitting the condition, not by an empty one.
export interface LockoutPolicyCondition {
  id?: number;
  condition_type: string;
  operator: string;
  value: string[];
}

// The values one condition references that are no longer valid, e.g. a realm that has since been
// deleted. Grouped by condition type so the editor can put the message under the right control.
export interface StaleConditionValues {
  condition_type: string;
  values: string[];
}

export interface LockoutPolicy {
  id: number;
  name: string;
  time_window_seconds: number;
  enabled: boolean;
  dry_run: boolean;
  priority: number;
  target: LockoutTarget;
  count_mode: CountMode;
  counter_types_to_track: AuthEventType[];
  stages: LockoutPolicyStage[];
  // Which requests the policy applies to at all. Optional: a policy without any restriction simply
  // has none, which is why the shipped templates carry no conditions key and why an editor with
  // nothing selected omits it from the payload rather than sending an empty list.
  conditions?: LockoutPolicyCondition[];
}

// The shape sent to create/update; id is only present (and ignored server-side) on update.
// priority is number | null in the draft: a new policy starts with no priority so the admin
// is forced to pick a deliberate, unique value (the backend requires it and 400s otherwise).
export type LockoutPolicySaveParams = Omit<LockoutPolicy, "id" | "priority"> & {
  id?: number;
  priority: number | null;
};

// What a shipped template carries: a create payload minus the priority, which the
// catalog deliberately omits so the admin picks a unique one. Optional (not just
// nullable) because the key is absent from the response altogether.
export type LockoutPolicyTemplateParams = Omit<LockoutPolicySaveParams, "priority"> & {
  priority?: number | null;
};

// A ready-made policy the backend ships (GET /conditionalaccess/template); "policy"
// is a full create payload a client prefills, edits and POSTs as a normal policy.
export interface LockoutPolicyTemplate {
  key: string;
  description: string;
  policy: LockoutPolicyTemplateParams;
}

export const EMPTY_LOCKOUT_POLICY: LockoutPolicySaveParams = {
  name: "",
  time_window_seconds: 600,
  enabled: true,
  dry_run: false,
  priority: null,
  target: "user",
  count_mode: "PER_REQUEST",
  counter_types_to_track: [],
  stages: []
};

export interface ConditionalAccessPolicyServiceInterface {
  readonly policiesResource: HttpResourceRef<PiResponse<LockoutPolicy[]> | undefined>;
  readonly policies: Signal<LockoutPolicy[]>;
  readonly eventTypesResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  readonly eventTypes: Signal<AuthEventType[]>;
  readonly actionTypesResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  readonly actionTypes: Signal<LockoutActionType[]>;
  readonly targetsResource: HttpResourceRef<PiResponse<Record<string, TargetConstraints>> | undefined>;
  readonly actionsByTarget: Signal<Record<LockoutTarget, LockoutActionType[]>>;
  readonly countModesByTarget: Signal<Record<LockoutTarget, CountMode[]>>;
  readonly targets: Signal<LockoutTarget[]>;
  readonly templatesResource: HttpResourceRef<PiResponse<LockoutPolicyTemplate[]> | undefined>;
  readonly templates: Signal<LockoutPolicyTemplate[]>;
  readonly conditionTypesResource: HttpResourceRef<PiResponse<Record<string, ConditionTypeMeta>> | undefined>;
  readonly conditionTypes: Signal<Record<string, ConditionTypeMeta>>;

  actionsForTarget(target: LockoutTarget): LockoutActionType[];

  countModesForTarget(target: LockoutTarget): CountMode[];

  operatorsForConditionType(conditionType: string): ConditionOperatorMeta[];

  choicesForConditionType(conditionType: string): string[] | null;

  staleConditionValues(conditions: LockoutPolicyCondition[] | undefined): StaleConditionValues[];

  savePolicy(policy: LockoutPolicySaveParams): Promise<number | undefined>;

  deletePolicy(id: number): Promise<void>;

  deleteWithConfirmDialog(policy: { id: number; name: string }): Promise<void>;

  deleteSelectedWithConfirmDialog(policies: { id: number; name: string }[]): Promise<boolean>;

  reorderPolicies(policyIds: number[], expectedPriorities?: number[]): Promise<boolean>;

  enablePolicy(id: number): Promise<void>;

  disablePolicy(id: number): Promise<void>;
}

@Injectable()
export class ConditionalAccessPolicyService implements ConditionalAccessPolicyServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  readonly baseUrl = environment.proxyUrl + "/conditionalaccess/policy";
  readonly eventTypesUrl = environment.proxyUrl + "/conditionalaccess/eventtypes";
  readonly actionTypesUrl = environment.proxyUrl + "/conditionalaccess/actiontypes";
  readonly targetsUrl = environment.proxyUrl + "/conditionalaccess/targets";
  readonly templatesUrl = environment.proxyUrl + "/conditionalaccess/template";
  readonly conditionTypesUrl = environment.proxyUrl + "/conditionalaccess/conditiontypes";

  readonly policiesResource = httpResource<PiResponse<LockoutPolicy[]>>(() => {
    if (!this.authService.actionAllowed("lockout_policy_read")) {
      return undefined;
    }
    if (!this.contentService.onConditionalAccess()) {
      return undefined;
    }
    return {
      url: this.baseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly policies: Signal<LockoutPolicy[]> = computed(() => {
    if (this.policiesResource.hasValue()) {
      return this.policiesResource.value()?.result?.value ?? [];
    }
    return [];
  });

  // The trackable authentication event types and the stage action types are served by the backend
  // (the authoritative enums) so the editor's selects cover newly added types without a WebUI change.
  readonly eventTypesResource = httpResource<PiResponse<string[]>>(() => {
    if (!this.authService.actionAllowed("lockout_policy_read") || !this.contentService.onConditionalAccess()) {
      return undefined;
    }
    return {
      url: this.eventTypesUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly eventTypes: Signal<AuthEventType[]> = computed(
    () => (this.eventTypesResource.value()?.result?.value ?? []) as AuthEventType[]
  );

  readonly actionTypesResource = httpResource<PiResponse<string[]>>(() => {
    if (!this.authService.actionAllowed("lockout_policy_read") || !this.contentService.onConditionalAccess()) {
      return undefined;
    }
    return {
      url: this.actionTypesUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly actionTypes: Signal<LockoutActionType[]> = computed(
    () => (this.actionTypesResource.value()?.result?.value ?? []) as LockoutActionType[]
  );

  // The targets and, per target, the constraints that depend on the target: the actions it allows and the count
  // modes it supports (see the TargetConstraints shape).
  readonly targetsResource = httpResource<PiResponse<Record<string, TargetConstraints>>>(() => {
    if (!this.authService.actionAllowed("lockout_policy_read") || !this.contentService.onConditionalAccess()) {
      return undefined;
    }
    return {
      url: this.targetsUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  private readonly targetConstraints: Signal<Record<LockoutTarget, TargetConstraints>> = computed(
    () => (this.targetsResource.value()?.result?.value ?? {}) as Record<LockoutTarget, TargetConstraints>
  );

  readonly actionsByTarget: Signal<Record<LockoutTarget, LockoutActionType[]>> = computed(
    () =>
      Object.fromEntries(
        Object.entries(this.targetConstraints()).map(([target, entry]) => [target, entry.actions])
      ) as Record<LockoutTarget, LockoutActionType[]>
  );

  readonly countModesByTarget: Signal<Record<LockoutTarget, CountMode[]>> = computed(
    () =>
      Object.fromEntries(
        Object.entries(this.targetConstraints()).map(([target, entry]) => [target, entry.count_modes])
      ) as Record<LockoutTarget, CountMode[]>
  );

  readonly targets: Signal<LockoutTarget[]> = computed(() => Object.keys(this.targetConstraints()) as LockoutTarget[]);

  readonly templatesResource = httpResource<PiResponse<LockoutPolicyTemplate[]>>(() => {
    if (!this.authService.actionAllowed("lockout_policy_read") || !this.contentService.onConditionalAccess()) {
      return undefined;
    }
    return {
      url: this.templatesUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly templates: Signal<LockoutPolicyTemplate[]> = computed(
    () => this.templatesResource.value()?.result?.value ?? []
  );

  // The condition vocabulary: per condition type its label, its operators and the values that are
  // valid right now. Fetched rather than hard-coded because the realm list changes as realms are
  // created and deleted, and a stale selection list would invite a condition that can never match.
  readonly conditionTypesResource = httpResource<PiResponse<Record<string, ConditionTypeMeta>>>(() => {
    if (!this.authService.actionAllowed("lockout_policy_read") || !this.contentService.onConditionalAccess()) {
      return undefined;
    }
    return {
      url: this.conditionTypesUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly conditionTypes: Signal<Record<string, ConditionTypeMeta>> = computed(
    () => this.conditionTypesResource.value()?.result?.value ?? {}
  );

  // Actions allowed for a target; falls back to the full list until /targets loads,
  // so the select is never empty on first paint.
  actionsForTarget(target: LockoutTarget): LockoutActionType[] {
    return this.actionsByTarget()[target] ?? this.actionTypes();
  }

  countModesForTarget(target: LockoutTarget): CountMode[] {
    return this.countModesByTarget()[target] ?? [];
  }

  // The operators a condition type permits, with their translated labels. Empty until
  // /conditiontypes loads; the editor falls back to its own labels so the control is never blank.
  operatorsForConditionType(conditionType: string): ConditionOperatorMeta[] {
    return this.conditionTypes()[conditionType]?.operators ?? [];
  }

  // The values currently valid for a condition type. null means "not enumerable" - either the type
  // genuinely has an open value space, or /conditiontypes has not loaded yet. Both are answered the
  // same way on purpose: nothing can be judged unknown without a vocabulary to judge it against.
  choicesForConditionType(conditionType: string): string[] | null {
    return this.conditionTypes()[conditionType]?.choices ?? null;
  }

  // The condition values that are no longer valid, e.g. a realm deleted after the policy was
  // written. These matter because the backend rejects them on write (_validate_condition_value),
  // so such a policy cannot be saved at all until they are dealt with - and because a condition
  // naming a value that no longer exists silently stopped doing what it was written to do.
  staleConditionValues(conditions: LockoutPolicyCondition[] | undefined): StaleConditionValues[] {
    return (conditions ?? [])
      .map((condition) => {
        const choices = this.choicesForConditionType(condition.condition_type);
        return {
          condition_type: condition.condition_type,
          values: choices === null ? [] : condition.value.filter((value) => !choices.includes(value))
        };
      })
      .filter((stale) => stale.values.length > 0);
  }

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.policiesResource.error(), "conditional-access policies");
    });
  }

  async savePolicy(policy: LockoutPolicySaveParams): Promise<number | undefined> {
    const headers = this.authService.getHeaders();
    const isUpdate = policy.id != null;
    const request = isUpdate
      ? this.http.patch<PiResponse<number>>(`${this.baseUrl}/${policy.id}`, policy, { headers })
      : this.http.post<PiResponse<number>>(this.baseUrl, policy, { headers });

    try {
      const response = await lastValueFrom(request);
      this.notificationService.success(
        isUpdate
          ? $localize`Successfully updated conditional-access policy.`
          : $localize`Successfully created conditional-access policy.`
      );
      this.policiesResource.reload();
      return response?.result?.value;
    } catch (error) {
      const httpError = error as HttpErrorResponse;
      const body = httpError.error as PiResponse<number> | undefined;
      const message = body?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to save conditional-access policy. ` + message);
      return undefined;
    }
  }

  async deletePolicy(id: number): Promise<void> {
    const headers = this.authService.getHeaders();
    const request = this.http.delete<PiResponse<number>>(`${this.baseUrl}/${id}`, { headers });

    try {
      await lastValueFrom(request);
      this.notificationService.success($localize`Successfully deleted conditional-access policy.`);
      this.policiesResource.reload();
    } catch (error) {
      const httpError = error as HttpErrorResponse;
      const body = httpError.error as PiResponse<number> | undefined;
      const message = body?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to delete conditional-access policy. ` + message);
    }
  }

  async deleteWithConfirmDialog(policy: { id: number; name: string }): Promise<void> {
    const confirmed = await this.dialogService.confirm({
      title: $localize`Delete Conditional-Access Policy`,
      message: $localize`Do you really want to delete the policy "${policy.name}"?`,
      confirmButtonText: $localize`Delete`
    });
    if (!confirmed) {
      return;
    }
    await this.deletePolicy(policy.id);
  }

  async deleteSelectedWithConfirmDialog(policies: { id: number; name: string }[]): Promise<boolean> {
    if (policies.length === 0) {
      return false;
    }
    const confirmed = await this.dialogService.confirm({
      title: $localize`Delete Conditional-Access Policies`,
      message: $localize`Do you really want to delete ${policies.length} selected policies?`,
      confirmButtonText: $localize`Delete`
    });
    if (!confirmed) {
      return false;
    }
    const headers = this.authService.getHeaders();
    try {
      await Promise.all(
        policies.map((policy) =>
          lastValueFrom(this.http.delete<PiResponse<number>>(`${this.baseUrl}/${policy.id}`, { headers }))
        )
      );
      this.notificationService.success($localize`Successfully deleted ${policies.length} conditional-access policies.`);
      this.policiesResource.reload();
      return true;
    } catch (error) {
      const httpError = error as HttpErrorResponse;
      const body = httpError.error as PiResponse<number> | undefined;
      const message = body?.result?.error?.message || "";
      this.notificationService.error($localize`Failed to delete conditional-access policies. ` + message);
      this.policiesResource.reload();
      return false;
    }
  }

  async enablePolicy(id: number): Promise<void> {
    const headers = this.authService.getHeaders();
    try {
      await lastValueFrom(this.http.patch(`${this.baseUrl}/${id}`, { enabled: true }, { headers }));
      this.policiesResource.reload();
    } catch {
      this.notificationService.error($localize`Failed to enable conditional-access policy.`);
      this.policiesResource.reload();
    }
  }

  async disablePolicy(id: number): Promise<void> {
    const headers = this.authService.getHeaders();
    try {
      await lastValueFrom(this.http.patch(`${this.baseUrl}/${id}`, { enabled: false }, { headers }));
      this.policiesResource.reload();
    } catch {
      this.notificationService.error($localize`Failed to disable conditional-access policy.`);
      this.policiesResource.reload();
    }
  }

  // Rearrange the evaluation order: the listed policies take the priority values this
  // same set already holds, in the given order. Only these policies change, so a single
  // swap sends two ids. See reorder_lockout_policies() for the invariant.
  //
  // expectedPriorities asserts what each policy held when the caller read it, so a
  // concurrent rearrangement comes back as a 409 instead of silently overwriting the
  // other admin. It covers only the submitted policies, so two admins reordering
  // different parts of the list do not get in each other's way.
  async reorderPolicies(policyIds: number[], expectedPriorities?: number[]): Promise<boolean> {
    const headers = this.authService.getHeaders();
    try {
      await lastValueFrom(
        this.http.put<PiResponse<boolean>>(
          `${this.baseUrl}/order`,
          { policy_ids: policyIds, ...(expectedPriorities ? { expected_priorities: expectedPriorities } : {}) },
          { headers }
        )
      );
      this.notificationService.success($localize`Successfully saved the new conditional-access policy order.`);
      this.policiesResource.reload();
      return true;
    } catch (error) {
      const httpError = error as HttpErrorResponse;
      const body = httpError.error as PiResponse<boolean> | undefined;
      const message = body?.result?.error?.message || "";
      // The API states the conflict but deliberately gives no advice on what to do about
      // it, so the wording for this client belongs here, keyed off the status code. The
      // reload below is what makes "refreshed" true, and the edit page re-seeds its draft
      // from it (see the reseed effect in ConditionalAccessComponent).
      this.notificationService.error(
        httpError.status === 409
          ? $localize`Someone else changed priorities while you were rearranging them. The list has been refreshed - please redo your changes. `
          : $localize`Failed to reorder conditional-access policies. ` + message
      );
      this.policiesResource.reload();
      return false;
    }
  }
}
