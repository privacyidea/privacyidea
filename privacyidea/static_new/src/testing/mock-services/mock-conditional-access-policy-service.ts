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
import { signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import {
  AuthEventType,
  ConditionalAccessPolicyServiceInterface,
  ConditionOperatorMeta,
  ConditionTypeMeta,
  CountMode,
  LockoutActionType,
  LockoutPolicy,
  LockoutPolicyCondition,
  LockoutPolicySaveParams,
  LockoutPolicyTemplate,
  LockoutStageAction,
  LockoutTarget,
  StaleConditionValues,
  TargetConstraints
} from "@services/conditional-access/conditional-access-policy.service";
import { MockHttpResourceRef, MockPiResponse } from "@testing/mock-services/mock-utils";
import { Observable, of } from "rxjs";

export class MockConditionalAccessPolicyService implements ConditionalAccessPolicyServiceInterface {
  policiesResource = new MockHttpResourceRef(MockPiResponse.fromValue<LockoutPolicy[]>([]));

  policies = signal<LockoutPolicy[]>([]);

  eventTypesResource = new MockHttpResourceRef(MockPiResponse.fromValue<string[]>([]));

  eventTypes = signal<AuthEventType[]>([]);

  actionTypesResource = new MockHttpResourceRef(MockPiResponse.fromValue<string[]>([]));

  actionTypes = signal<LockoutActionType[]>([]);

  targetsResource = new MockHttpResourceRef(MockPiResponse.fromValue<Record<string, TargetConstraints>>({}));

  actionsByTarget = signal<Record<LockoutTarget, LockoutActionType[]>>(
    {} as Record<LockoutTarget, LockoutActionType[]>
  );

  countModesByTarget = signal<Record<LockoutTarget, CountMode[]>>({} as Record<LockoutTarget, CountMode[]>);
  // Empty by default, so a spec that does not opt in sees no per-stage action rules and is not gated by them.
  repeatableActionsByTarget = signal<Record<LockoutTarget, LockoutActionType[]>>(
    {} as Record<LockoutTarget, LockoutActionType[]>
  );
  exclusiveGroupsByTarget = signal<Record<LockoutTarget, LockoutActionType[][]>>(
    {} as Record<LockoutTarget, LockoutActionType[][]>
  );

  targets = signal<LockoutTarget[]>([]);

  templatesResource = new MockHttpResourceRef(MockPiResponse.fromValue<LockoutPolicyTemplate[]>([]));

  templates = signal<LockoutPolicyTemplate[]>([]);

  conditionTypesResource = new MockHttpResourceRef(MockPiResponse.fromValue<Record<string, ConditionTypeMeta>>({}));

  conditionTypes = signal<Record<string, ConditionTypeMeta>>({});

  operatorsForConditionType = jest.fn(
    (conditionType: string): ConditionOperatorMeta[] => this.conditionTypes()[conditionType]?.operators ?? []
  );

  choicesForConditionType = jest.fn(
    (conditionType: string): string[] | null => this.conditionTypes()[conditionType]?.choices ?? null
  );

  staleConditionValues = jest.fn((conditions: LockoutPolicyCondition[] | undefined): StaleConditionValues[] =>
    (conditions ?? [])
      .map((condition) => {
        const choices = this.choicesForConditionType(condition.condition_type);
        return {
          condition_type: condition.condition_type,
          values: choices === null ? [] : condition.value.filter((value) => !choices.includes(value))
        };
      })
      .filter((stale) => stale.values.length > 0)
  );

  actionsForTarget = jest.fn(
    (target: LockoutTarget): LockoutActionType[] => this.actionsByTarget()[target] ?? this.actionTypes()
  );

  countModesForTarget = jest.fn((target: LockoutTarget): CountMode[] => this.countModesByTarget()[target] ?? []);

  unavailableActionTypes = jest.fn(
    (actions: LockoutStageAction[], target: LockoutTarget, exceptIndex?: number): Set<LockoutActionType> => {
      const repeatable = new Set(this.repeatableActionsByTarget()[target] ?? []);
      const groups = this.exclusiveGroupsByTarget()[target] ?? [];
      const unavailable = new Set<LockoutActionType>();
      if (repeatable.size === 0 && groups.length === 0) {
        return unavailable;
      }
      const present = actions.filter((_, index) => index !== exceptIndex).map((action) => action.action_type);
      for (const actionType of present) {
        if (!repeatable.has(actionType)) {
          unavailable.add(actionType);
        }
        for (const group of groups) {
          if (group.includes(actionType)) {
            group.forEach((member) => unavailable.add(member));
          }
        }
      }
      return unavailable;
    }
  );

  actionConflict = jest.fn(
    (actions: LockoutStageAction[], index: number, target: LockoutTarget): "duplicate" | "exclusive" | null => {
      const action = actions[index];
      if (!action) {
        return null;
      }
      const repeatable = new Set(this.repeatableActionsByTarget()[target] ?? []);
      const groups = this.exclusiveGroupsByTarget()[target] ?? [];
      if (repeatable.size === 0 && groups.length === 0) {
        return null;
      }
      const earlier = actions.slice(0, index).map((other) => other.action_type);
      if (!repeatable.has(action.action_type) && earlier.includes(action.action_type)) {
        return "duplicate";
      }
      const conflicting = groups.some(
        (group) =>
          group.includes(action.action_type) &&
          earlier.some((type) => type !== action.action_type && group.includes(type))
      );
      return conflicting ? "exclusive" : null;
    }
  );

  getPolicies = jest.fn(
    (): Observable<PiResponse<LockoutPolicy[]>> => of(MockPiResponse.fromValue<LockoutPolicy[]>(this.policies()))
  );

  savePolicy = jest.fn(async (_: LockoutPolicySaveParams): Promise<number | undefined> => Promise.resolve(1));

  deletePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  deleteWithConfirmDialog = jest.fn(async (): Promise<void> => Promise.resolve());

  deleteSelectedWithConfirmDialog = jest.fn(async (): Promise<boolean> => Promise.resolve(true));

  enablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  disablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  setDryRun = jest.fn(async (_: number, __: boolean): Promise<void> => Promise.resolve());

  reorderPolicies = jest.fn(async (_: number[]): Promise<boolean> => Promise.resolve(true));
}
