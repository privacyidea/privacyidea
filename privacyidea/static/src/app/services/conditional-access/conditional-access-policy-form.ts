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

import {
  applyEach,
  disabled,
  maxLength,
  min,
  PathKind,
  required,
  SchemaPath,
  SchemaPathRules,
  schema,
  validate
} from "@angular/forms/signals";
import { deepCopy } from "@utils/deep-copy.utils";
import { DURATION_UNIT_FACTORS, DurationUnit, largestWholeDurationUnit } from "@utils/duration-unit.utils";
import { ERR, requiredNonBlank } from "@utils/form-rules.utils";
import {
  AuthEventType,
  ConditionalAccessPolicyCondition,
  ConditionalAccessPolicySaveParams,
  ConditionalAccessPolicyServiceInterface,
  ConditionalAccessPolicyStage,
  ConditionalAccessStageAction,
  ConditionalAccessTarget,
  CountMode,
  STANDING_DECISION_ACTIONS,
  actionValueError
} from "./conditional-access-policy.service";

// Error kinds the policy form emits beyond the generic ones in ERR.
export const CA_ERR = {
  notInteger: "notInteger",
  priorityTaken: "priorityTaken",
  countModeNotAllowed: "countModeNotAllowed",
  stageThreshold: "stageThreshold",
  stageThresholdDuplicate: "stageThresholdDuplicate",
  stageActionNotAllowed: "stageActionNotAllowed",
  stageActionValue: "stageActionValue",
  stageActionConflict: "stageActionConflict",
  staleConditionValue: "staleConditionValue"
} as const;

// Mirrors the Unicode(255) of the name column in privacyidea/models/conditional_access_policy.py.
export const MAX_POLICY_NAME_LENGTH = 255;

// Mirrors the Unicode(255) of the name column of a stage in privacyidea/models/conditional_access_policy.py.
export const MAX_STAGE_NAME_LENGTH = 255;

// Mirrors MAX_ERROR_MESSAGE_LENGTH in privacyidea.lib.conditional_access.policy (Unicode(500) in the model).
export const MAX_ERROR_MESSAGE_LENGTH = 500;

// What a stage of the policy editor binds its fields to. The name holds the text of its input and the specific error
// message is on or off through has_error_message, so each field is always present and the message field can be
// disabled while it is off; toPolicySaveParams maps the stage back to the stored shape.
export interface ConditionalAccessStageFormModel {
  id: number | null;
  name: string;
  has_error_message: boolean;
  error_message: string;
  failure_threshold: number | null;
  actions: ConditionalAccessStageAction[];
}

// What the policy editor binds its fields to. The numeric fields hold the text of their input, so an entry that is
// not a number is reported where it was typed instead of being rewritten; toPolicySaveParams converts them at the
// save boundary. Fields without an input of their own (stages, conditions, the toggles, the read-only metadata) ride
// along so the form holds the whole policy.
export interface ConditionalAccessPolicyFormModel {
  id: number | null;
  name: string;
  time_window_value: string;
  time_window_unit: DurationUnit;
  enabled: boolean;
  dry_run: boolean;
  enforced_since: string | null;
  priority: string;
  target: ConditionalAccessTarget;
  count_mode: CountMode;
  reset_on_success: boolean;
  counter_types_to_track: AuthEventType[];
  stages: ConditionalAccessStageFormModel[];
  conditions: ConditionalAccessPolicyCondition[];
  reset_counters_on_enforce: boolean | null;
}

// The whole number the text holds, or null for empty text and for anything else.
export function parseWholeNumber(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed === "") {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) ? parsed : null;
}

// The form model of a stage. A stage without a message is off; one holding an empty message is on but not written yet.
export function toStageFormModel(stage: ConditionalAccessPolicyStage): ConditionalAccessStageFormModel {
  return {
    id: stage.id ?? null,
    name: stage.name ?? "",
    has_error_message: stage.error_message !== null && stage.error_message !== undefined,
    error_message: stage.error_message ?? "",
    failure_threshold: stage.failure_threshold,
    actions: deepCopy(stage.actions)
  };
}

// The stored shape of a stage. The backend strips the name and reads a blank name and a missing message as none, so a
// name made of spaces and a message that is off are left out. A threshold that is not a number yields 0, which the
// form rejects before anything is sent unless the stage carries only DENY.
export function toStageSaveParams(stage: ConditionalAccessStageFormModel): ConditionalAccessPolicyStage {
  const params: ConditionalAccessPolicyStage = {
    failure_threshold: stage.failure_threshold ?? 0,
    actions: stage.actions
  };
  if (stage.id !== null) {
    params.id = stage.id;
  }
  const name = stage.name.trim();
  if (name) {
    params.name = name;
  }
  if (stage.has_error_message) {
    params.error_message = stage.error_message;
  }
  return params;
}

// The form model of a policy. A saved window shows in the coarsest unit that divides it evenly, e.g. "10 minutes"
// rather than "600 seconds".
export function toPolicyFormModel(policy: ConditionalAccessPolicySaveParams): ConditionalAccessPolicyFormModel {
  const unit = largestWholeDurationUnit(policy.time_window_seconds);
  return {
    id: policy.id ?? null,
    name: policy.name,
    time_window_value: String(policy.time_window_seconds / DURATION_UNIT_FACTORS[unit]),
    time_window_unit: unit,
    enabled: policy.enabled,
    dry_run: policy.dry_run,
    enforced_since: policy.enforced_since ?? null,
    priority: policy.priority == null ? "" : String(policy.priority),
    target: policy.target,
    count_mode: policy.count_mode,
    reset_on_success: policy.reset_on_success,
    counter_types_to_track: deepCopy(policy.counter_types_to_track),
    stages: policy.stages.map(toStageFormModel),
    conditions: deepCopy(policy.conditions ?? []),
    reset_counters_on_enforce: policy.reset_counters_on_enforce ?? null
  };
}

// The payload the backend takes. Text that is not a whole number yields priority null and a window of 0 seconds, both
// of which the form rejects before anything is sent. A policy without conditions omits the key, because the backend
// only replaces conditions when it is present.
export function toPolicySaveParams(model: ConditionalAccessPolicyFormModel): ConditionalAccessPolicySaveParams {
  const windowValue = parseWholeNumber(model.time_window_value);
  const params: ConditionalAccessPolicySaveParams = {
    name: model.name,
    time_window_seconds: windowValue === null ? 0 : windowValue * DURATION_UNIT_FACTORS[model.time_window_unit],
    enabled: model.enabled,
    dry_run: model.dry_run,
    enforced_since: model.enforced_since,
    priority: parseWholeNumber(model.priority),
    target: model.target,
    count_mode: model.count_mode,
    reset_on_success: model.reset_on_success,
    counter_types_to_track: model.counter_types_to_track,
    stages: model.stages.map(toStageSaveParams)
  };
  if (model.id !== null) {
    params.id = model.id;
  }
  if (model.conditions.length) {
    params.conditions = model.conditions;
  }
  if (model.reset_counters_on_enforce !== null) {
    params.reset_counters_on_enforce = model.reset_counters_on_enforce;
  }
  return params;
}

// A required text field that must hold a whole number of at least 1. The kinds are `required` for empty or blank text,
// `notInteger` for a number with a fraction and `min` for a number below 1.
export function requiredPositiveWholeNumber(path: SchemaPath<string>): void {
  requiredNonBlank(path);
  validate(path, (ctx) => {
    const text = ctx.value();
    if (text.trim() === "") {
      return [];
    }
    const parsed = parseWholeNumber(text);
    if (parsed === null) {
      return [{ kind: CA_ERR.notInteger }];
    }
    return parsed >= 1 ? [] : [{ kind: ERR.min }];
  });
}

// Why an action collides with another one of its stage: the same action twice, or two actions that contradict each
// other.
export function actionConflictMessage(conflict: "duplicate" | "exclusive"): string {
  return conflict === "duplicate"
    ? $localize`:@@conditionalAccess.actionAlreadyStageOnly:This action is already on this stage. Only the email actions may be added more than once.`
    : $localize`:@@conditionalAccess.actionContradictsAnotherAction:This action contradicts another action on this stage. Remove one of them.`;
}

// A threshold counts failures, so it starts at 1. The exception the backend also makes
// (_validate_threshold_for_actions): a stage whose every action is a standing DENY verdict may use 0, which then
// means "always" - the lockdown idiom.
export function stageThresholdAllowed(stage: {
  failure_threshold: number | null;
  actions: ConditionalAccessStageAction[];
}): boolean {
  const threshold = stage.failure_threshold;
  return (
    threshold !== null &&
    (threshold >= 1 ||
      (threshold === 0 &&
        stage.actions.length > 0 &&
        stage.actions.every((action) => STANDING_DECISION_ACTIONS.includes(action.action_type))))
  );
}

// The rules of one stage that need nothing from outside it. The threshold is a whole number and, below 1, only a
// DENY-only stage may use 0 (CA_ERR.stageThreshold); the specific error message is writable only while it is on.
export const stageSchema = schema<ConditionalAccessStageFormModel>((stage) => {
  maxLength(stage.name, MAX_STAGE_NAME_LENGTH);
  required(stage.failure_threshold);
  min(stage.failure_threshold, 0);
  validate(stage.failure_threshold, (ctx) => {
    const threshold = ctx.value();
    return threshold !== null && !Number.isInteger(threshold) ? [{ kind: CA_ERR.notInteger }] : [];
  });
  validate(stage.failure_threshold, (ctx) =>
    ctx.value() === 0 && !stageThresholdAllowed({ failure_threshold: 0, actions: ctx.valueOf(stage.actions) })
      ? [{ kind: CA_ERR.stageThreshold }]
      : []
  );
  disabled(stage.error_message, (ctx) => !ctx.valueOf(stage.has_error_message));
  maxLength(stage.error_message, MAX_ERROR_MESSAGE_LENGTH);
});

// The rules of the actions of one stage, which depend on the policy's target and on the rules the server serves for
// it. Until /targets has loaded, the rules that compare against it cannot judge and let the action pass; the backend
// enforces them either way. Each rule reports on the action itself, so its item shows what is wrong with it.
export function applyActionRules(
  actions: SchemaPath<ConditionalAccessStageAction[], SchemaPathRules.Supported, PathKind.Child>,
  target: SchemaPath<ConditionalAccessTarget, SchemaPathRules.Supported, PathKind.Child>,
  policyService: Pick<ConditionalAccessPolicyServiceInterface, "actionsForTarget" | "actionConflict">
): void {
  applyEach(actions, (action) => {
    // Every stage action must be allowed for the selected target, matching the backend's _ACTIONS_BY_TARGET check;
    // the action select only offers compatible actions, but switching an existing policy's target can leave a stale,
    // now-incompatible action behind.
    validate(action, (ctx) => {
      const allowed = policyService.actionsForTarget(ctx.valueOf(target));
      return allowed.length === 0 || allowed.includes(ctx.value().action_type)
        ? []
        : [{ kind: CA_ERR.stageActionNotAllowed }];
    });
    // Within one stage an action may appear only once (except the email actions), and the timed/permanent pairs may
    // not be combined; the backend rejects them (_validate_stage_action_combination). The message names which of the
    // two it is.
    validate(action, (ctx) => {
      const conflict = policyService.actionConflict(ctx.valueOf(actions), ctx.index(), ctx.valueOf(target));
      return conflict === null ? [] : [{ kind: CA_ERR.stageActionConflict, message: actionConflictMessage(conflict) }];
    });
    // Every stage action must carry an action_value its type can act on (the backend enforces the same via
    // _ACTION_VALUE_VALIDATORS); the message says what is missing.
    validate(action, (ctx) => {
      const message = actionValueError(ctx.value());
      return message === null ? [] : [{ kind: CA_ERR.stageActionValue, message }];
    });
  });
}
