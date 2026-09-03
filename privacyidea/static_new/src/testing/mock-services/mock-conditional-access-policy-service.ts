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
  ConditionalAccessActionType,
  ConditionalAccessPolicy,
  ConditionalAccessPolicyCondition,
  ConditionalAccessPolicySaveParams,
  ConditionalAccessPolicyTemplate,
  ConditionalAccessStageAction,
  ConditionalAccessTarget,
  DefaultErrorMessage,
  StaleConditionValues,
  TargetConstraints
} from "@services/conditional-access/conditional-access-policy.service";
import { MockHttpResourceRef, MockPiResponse } from "@testing/mock-services/mock-utils";
import { Observable, of } from "rxjs";

export class MockConditionalAccessPolicyService implements ConditionalAccessPolicyServiceInterface {
  policiesResource = new MockHttpResourceRef(MockPiResponse.fromValue<ConditionalAccessPolicy[]>([]));

  policies = signal<ConditionalAccessPolicy[]>([]);

  eventTypesResource = new MockHttpResourceRef(MockPiResponse.fromValue<string[]>([]));

  eventTypes = signal<AuthEventType[]>([]);

  actionTypesResource = new MockHttpResourceRef(MockPiResponse.fromValue<string[]>([]));

  actionTypes = signal<ConditionalAccessActionType[]>([]);

  targetsResource = new MockHttpResourceRef(MockPiResponse.fromValue<Record<string, TargetConstraints>>({}));

  actionsByTarget = signal<Record<ConditionalAccessTarget, ConditionalAccessActionType[]>>(
    {} as Record<ConditionalAccessTarget, ConditionalAccessActionType[]>
  );

  countModesByTarget = signal<Record<ConditionalAccessTarget, CountMode[]>>(
    {} as Record<ConditionalAccessTarget, CountMode[]>
  );
  // Empty by default, so a spec that does not opt in sees no per-stage action rules and is not gated by them.
  repeatableActionsByTarget = signal<Record<ConditionalAccessTarget, ConditionalAccessActionType[]>>(
    {} as Record<ConditionalAccessTarget, ConditionalAccessActionType[]>
  );
  exclusiveGroupsByTarget = signal<Record<ConditionalAccessTarget, ConditionalAccessActionType[][]>>(
    {} as Record<ConditionalAccessTarget, ConditionalAccessActionType[][]>
  );

  targets = signal<ConditionalAccessTarget[]>([]);

  templatesResource = new MockHttpResourceRef(MockPiResponse.fromValue<ConditionalAccessPolicyTemplate[]>([]));

  templates = signal<ConditionalAccessPolicyTemplate[]>([]);

  defaultErrorMessagesResource = new MockHttpResourceRef(MockPiResponse.fromValue<DefaultErrorMessage[]>([]));

  defaultErrorMessages = signal<DefaultErrorMessage[]>([]);

  conditionTypesResource = new MockHttpResourceRef(MockPiResponse.fromValue<Record<string, ConditionTypeMeta>>({}));

  conditionTypes = signal<Record<string, ConditionTypeMeta>>({});

  operatorsForConditionType = jest.fn(
    (conditionType: string): ConditionOperatorMeta[] => this.conditionTypes()[conditionType]?.operators ?? []
  );

  choicesForConditionType = jest.fn(
    (conditionType: string): string[] | null => this.conditionTypes()[conditionType]?.choices ?? null
  );

  staleConditionValues = jest.fn((conditions: ConditionalAccessPolicyCondition[] | undefined): StaleConditionValues[] =>
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
    (target: ConditionalAccessTarget): ConditionalAccessActionType[] =>
      this.actionsByTarget()[target] ?? this.actionTypes()
  );

  countModesForTarget = jest.fn(
    (target: ConditionalAccessTarget): CountMode[] => this.countModesByTarget()[target] ?? []
  );

  // Canned - not a reimplementation of the real service's rules (see conditional-access-policy.service.spec.ts
  // for those). A spec drives its case with mockReturnValue/mockImplementation.
  unavailableActionTypes = jest.fn(
    (
      _actions: ConditionalAccessStageAction[],
      _target: ConditionalAccessTarget,
      _exceptIndex?: number
    ): Set<ConditionalAccessActionType> => new Set()
  );

  actionConflict = jest.fn(
    (
      _actions: ConditionalAccessStageAction[],
      _index: number,
      _target: ConditionalAccessTarget
    ): "duplicate" | "exclusive" | null => null
  );

  getPolicies = jest.fn(
    (): Observable<PiResponse<ConditionalAccessPolicy[]>> =>
      of(MockPiResponse.fromValue<ConditionalAccessPolicy[]>(this.policies()))
  );

  savePolicy = jest.fn(async (_: ConditionalAccessPolicySaveParams): Promise<number | undefined> => Promise.resolve(1));

  deletePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  deleteWithConfirmDialog = jest.fn(async (): Promise<void> => Promise.resolve());

  deleteSelectedWithConfirmDialog = jest.fn(async (): Promise<boolean> => Promise.resolve(true));

  enablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  disablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  setDryRun = jest.fn(async (_: number, __: boolean): Promise<void> => Promise.resolve());

  reorderPolicies = jest.fn(async (_: number[]): Promise<boolean> => Promise.resolve(true));
}
