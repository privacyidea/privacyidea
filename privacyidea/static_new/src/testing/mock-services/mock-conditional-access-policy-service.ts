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
  LockoutTarget,
  StaleConditionValues,
  TargetConstraints
} from "@services/conditional-access/conditional-access-policy.service";
import { MockHttpResourceRef, MockPiResponse } from "@testing/mock-services/mock-utils";

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

  savePolicy = jest.fn(async (_: LockoutPolicySaveParams): Promise<number | undefined> => Promise.resolve(1));

  deletePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  deleteWithConfirmDialog = jest.fn(async (): Promise<void> => Promise.resolve());

  deleteSelectedWithConfirmDialog = jest.fn(async (): Promise<boolean> => Promise.resolve(true));

  enablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  disablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  reorderPolicies = jest.fn(async (_: number[]): Promise<boolean> => Promise.resolve(true));
}
