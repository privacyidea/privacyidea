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
import { TestBed } from "@angular/core/testing";
import { applyEach, form } from "@angular/forms/signals";
import { ERR } from "@utils/form-rules.utils";
import {
  actionConflictMessage,
  applyActionRules,
  CA_ERR,
  ConditionalAccessPolicyFormModel,
  ConditionalAccessStageFormModel,
  MAX_ERROR_MESSAGE_LENGTH,
  MAX_STAGE_NAME_LENGTH,
  parseWholeNumber,
  requiredPositiveWholeNumber,
  stageSchema,
  stageThresholdAllowed,
  toPolicyFormModel,
  toPolicySaveParams,
  toStageFormModel,
  toStageSaveParams
} from "./conditional-access-policy-form";
import {
  ConditionalAccessPolicySaveParams,
  ConditionalAccessStageAction,
  ConditionalAccessTarget
} from "./conditional-access-policy.service";

const storedPolicy = (): ConditionalAccessPolicySaveParams => ({
  id: 4,
  name: "Brute Force",
  time_window_seconds: 600,
  enabled: true,
  dry_run: true,
  enforced_since: "2026-01-01T00:00:00",
  priority: 3,
  target: "user",
  count_mode: "PER_REQUEST",
  reset_on_success: true,
  counter_types_to_track: ["PIN_FAIL"],
  stages: [{ failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: 600 }] }],
  conditions: [{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }],
  reset_counters_on_enforce: false
});

describe("conditional-access-policy-form", () => {
  describe("parseWholeNumber", () => {
    it.each([
      ["5", 5],
      [" 12 ", 12],
      ["0", 0],
      ["-3", -3],
      ["1e2", 100]
    ])("reads %j as %d", (text, expected) => {
      expect(parseWholeNumber(text)).toBe(expected);
    });

    it.each(["", "   ", "abc", "1.5", "NaN", "Infinity"])("reads %j as no whole number", (text) => {
      expect(parseWholeNumber(text)).toBeNull();
    });
  });

  describe("toPolicyFormModel", () => {
    it.each([
      [3600, "hours", "1"],
      [7200, "hours", "2"],
      [600, "minutes", "10"],
      [90, "seconds", "90"]
    ])("shows a window of %ds in %s", (seconds, unit, value) => {
      const model = toPolicyFormModel({ ...storedPolicy(), time_window_seconds: seconds });
      expect(model.time_window_unit).toBe(unit);
      expect(model.time_window_value).toBe(value);
    });

    it("holds the priority as text, empty for none", () => {
      expect(toPolicyFormModel(storedPolicy()).priority).toBe("3");
      expect(toPolicyFormModel({ ...storedPolicy(), priority: null }).priority).toBe("");
    });

    it("spells absent optional keys as null and absent conditions as an empty list", () => {
      const bare = storedPolicy();
      delete bare.id;
      delete bare.enforced_since;
      delete bare.conditions;
      delete bare.reset_counters_on_enforce;
      expect(toPolicyFormModel(bare)).toEqual(
        expect.objectContaining({ id: null, enforced_since: null, conditions: [], reset_counters_on_enforce: null })
      );
    });

    it("copies the stages, conditions and counter types", () => {
      const policy = storedPolicy();
      const model = toPolicyFormModel(policy);
      model.stages[0].failure_threshold = 99;
      model.conditions[0].value.push("support");
      model.counter_types_to_track.push("PASSWORD_FAIL");
      expect(policy.stages[0].failure_threshold).toBe(5);
      expect(policy.conditions![0].value).toEqual(["sales"]);
      expect(policy.counter_types_to_track).toEqual(["PIN_FAIL"]);
    });
  });

  describe("toStageFormModel", () => {
    it("spells absent optional keys as an empty name, no id and no message", () => {
      expect(toStageFormModel({ failure_threshold: 3, actions: [] })).toEqual({
        id: null,
        name: "",
        has_error_message: false,
        error_message: "",
        failure_threshold: 3,
        actions: []
      });
    });

    it("keeps the id, the name and the message of a stored stage", () => {
      expect(
        toStageFormModel({ id: 7, name: "Warn", error_message: "Locked.", failure_threshold: 3, actions: [] })
      ).toEqual(expect.objectContaining({ id: 7, name: "Warn", has_error_message: true, error_message: "Locked." }));
    });

    it("holds an empty message as on but not written yet, and a null message as off", () => {
      expect(toStageFormModel({ error_message: "", failure_threshold: 1, actions: [] }).has_error_message).toBe(true);
      expect(toStageFormModel({ error_message: null, failure_threshold: 1, actions: [] }).has_error_message).toBe(
        false
      );
    });

    it("copies the actions", () => {
      const stage = { failure_threshold: 1, actions: [{ action_type: "LOCK_USER" as const, action_value: 60 }] };
      toStageFormModel(stage).actions[0].action_value = 5;
      expect(stage.actions[0].action_value).toBe(60);
    });
  });

  describe("toStageSaveParams", () => {
    const stageModel = (override: Partial<ConditionalAccessStageFormModel> = {}): ConditionalAccessStageFormModel => ({
      ...toStageFormModel({ failure_threshold: 5, actions: [] }),
      ...override
    });

    it("maps a stored stage back to itself", () => {
      const stored = { id: 7, name: "Warn", error_message: "Locked.", failure_threshold: 3, actions: [] };
      expect(toStageSaveParams(toStageFormModel(stored))).toEqual(stored);
    });

    it("leaves out the id, a blank name and a message that is off", () => {
      const params = toStageSaveParams(stageModel({ name: "   ", error_message: "stale", has_error_message: false }));
      expect(params).toEqual({ failure_threshold: 5, actions: [] });
    });

    it("strips the name", () => {
      expect(toStageSaveParams(stageModel({ name: "  Warn  " })).name).toBe("Warn");
    });

    it("sends a message that is on as written, empty included", () => {
      expect(toStageSaveParams(stageModel({ has_error_message: true, error_message: "" })).error_message).toBe("");
    });

    it("sends a threshold of 0 for an empty threshold", () => {
      expect(toStageSaveParams(stageModel({ failure_threshold: null })).failure_threshold).toBe(0);
    });
  });

  describe("toPolicySaveParams", () => {
    it("maps a stored policy back to itself", () => {
      expect(toPolicySaveParams(toPolicyFormModel(storedPolicy()))).toEqual(storedPolicy());
    });

    it("maps the stages through the stage mapper", () => {
      const model = toPolicyFormModel(storedPolicy());
      model.stages[0].name = " Warn ";
      expect(toPolicySaveParams(model).stages[0].name).toBe("Warn");
    });

    it("leaves out the id, the conditions and the enforce choice when the policy has none", () => {
      const model: ConditionalAccessPolicyFormModel = {
        ...toPolicyFormModel(storedPolicy()),
        id: null,
        conditions: [],
        reset_counters_on_enforce: null
      };
      const params = toPolicySaveParams(model);
      expect(params).not.toHaveProperty("id");
      expect(params).not.toHaveProperty("conditions");
      expect(params).not.toHaveProperty("reset_counters_on_enforce");
    });

    it("converts the window text and unit to seconds", () => {
      const model = {
        ...toPolicyFormModel(storedPolicy()),
        time_window_value: "3",
        time_window_unit: "hours" as const
      };
      expect(toPolicySaveParams(model).time_window_seconds).toBe(10800);
    });

    it.each(["", "abc", "1.5"])("sends a window of 0 seconds for the text %j", (text) => {
      const model = { ...toPolicyFormModel(storedPolicy()), time_window_value: text };
      expect(toPolicySaveParams(model).time_window_seconds).toBe(0);
    });

    it.each([
      ["7", 7],
      ["", null],
      ["abc", null],
      ["1.5", null]
    ])("converts the priority text %j to %p", (text, expected) => {
      const model = { ...toPolicyFormModel(storedPolicy()), priority: text };
      expect(toPolicySaveParams(model).priority).toBe(expected);
    });
  });

  describe("requiredPositiveWholeNumber", () => {
    const kindsFor = (text: string): string[] => {
      const model = signal({ amount: text });
      const f = TestBed.runInInjectionContext(() => form(model, (p) => requiredPositiveWholeNumber(p.amount)));
      return f
        .amount()
        .errors()
        .map((error) => error.kind);
    };

    it.each(["1", "7", " 12 "])("accepts %j", (text) => {
      expect(kindsFor(text)).toEqual([]);
    });

    it.each(["", "   "])("reports blank text %j as required", (text) => {
      expect(kindsFor(text)).toEqual([ERR.required]);
    });

    it.each(["1.5", "abc"])("reports %j as not an integer", (text) => {
      expect(kindsFor(text)).toEqual([CA_ERR.notInteger]);
    });

    it.each(["0", "-4"])("reports %j as below the minimum", (text) => {
      expect(kindsFor(text)).toEqual([ERR.min]);
    });
  });

  describe("stageThresholdAllowed", () => {
    const stage = (failure_threshold: number, ...types: string[]) => ({
      failure_threshold,
      actions: types.map((action_type) => ({ action_type, action_value: null }) as never)
    });

    it.each([[1], [5]])("allows a threshold of %d whatever the actions", (threshold) => {
      expect(stageThresholdAllowed(stage(threshold))).toBe(true);
      expect(stageThresholdAllowed(stage(threshold, "LOCK_USER"))).toBe(true);
    });

    it("rejects a stage without a threshold", () => {
      expect(stageThresholdAllowed({ failure_threshold: null, actions: [] })).toBe(false);
    });

    it("allows 0 for a stage carrying only a standing DENY", () => {
      expect(stageThresholdAllowed(stage(0, "DENY"))).toBe(true);
    });

    it.each([
      ["no action", stage(0)],
      ["a counting action", stage(0, "LOCK_USER")],
      ["a standing verdict mixed with a counting action", stage(0, "DENY", "LOCK_USER")],
      ["a negative threshold", stage(-1, "DENY")]
    ])("rejects %s", (_label, candidate) => {
      expect(stageThresholdAllowed(candidate)).toBe(false);
    });
  });

  describe("stageSchema", () => {
    const stageTree = (override: Partial<ConditionalAccessStageFormModel> = {}) => {
      const model = signal({ stages: [{ ...toStageFormModel({ failure_threshold: 5, actions: [] }), ...override }] });
      const tree = TestBed.runInInjectionContext(() => form(model, (p) => applyEach(p.stages, stageSchema)));
      return tree.stages[0];
    };
    const kinds = (field: () => { errors(): { kind: string }[] }) =>
      field()
        .errors()
        .map((error) => error.kind);
    const denyOnly = [{ action_type: "DENY" as const, action_value: null }];
    const lock = { action_type: "LOCK_USER" as const, action_value: 60 };

    it("accepts a whole threshold of 1 or more", () => {
      expect(stageTree({ failure_threshold: 1 })().valid()).toBe(true);
      expect(stageTree({ failure_threshold: 40 })().valid()).toBe(true);
    });

    it("requires a threshold", () => {
      expect(kinds(stageTree({ failure_threshold: null }).failure_threshold)).toEqual([ERR.required]);
    });

    it("rejects a negative threshold", () => {
      expect(kinds(stageTree({ failure_threshold: -1 }).failure_threshold)).toEqual([ERR.min]);
    });

    it("rejects a threshold with a fraction", () => {
      expect(kinds(stageTree({ failure_threshold: 1.5 }).failure_threshold)).toEqual([CA_ERR.notInteger]);
    });

    it("allows 0 only on a stage carrying only DENY", () => {
      expect(kinds(stageTree({ failure_threshold: 0, actions: denyOnly }).failure_threshold)).toEqual([]);
      expect(kinds(stageTree({ failure_threshold: 0, actions: [] }).failure_threshold)).toEqual([
        CA_ERR.stageThreshold
      ]);
      expect(kinds(stageTree({ failure_threshold: 0, actions: [...denyOnly, lock] }).failure_threshold)).toEqual([
        CA_ERR.stageThreshold
      ]);
    });

    it("limits the name length", () => {
      expect(kinds(stageTree({ name: "x".repeat(MAX_STAGE_NAME_LENGTH) }).name)).toEqual([]);
      expect(kinds(stageTree({ name: "x".repeat(MAX_STAGE_NAME_LENGTH + 1) }).name)).toEqual([ERR.maxLength]);
    });

    it("disables the message while it is off and leaves it enabled while it is on", () => {
      expect(stageTree({ has_error_message: false }).error_message().disabled()).toBe(true);
      expect(stageTree({ has_error_message: true }).error_message().disabled()).toBe(false);
    });

    it("limits the message length while it is on", () => {
      const long = "x".repeat(MAX_ERROR_MESSAGE_LENGTH + 1);
      expect(kinds(stageTree({ has_error_message: true, error_message: long }).error_message)).toEqual([ERR.maxLength]);
      expect(kinds(stageTree({ has_error_message: false, error_message: long }).error_message)).toEqual([]);
    });
  });

  describe("applyActionRules", () => {
    const action = (action_type: ConditionalAccessStageAction["action_type"], action_value: unknown = null) =>
      ({ action_type, action_value }) as ConditionalAccessStageAction;

    const rules = (
      actions: ConditionalAccessStageAction[],
      service: {
        actionsForTarget: (target: ConditionalAccessTarget) => ConditionalAccessStageAction["action_type"][];
        actionConflict: (...args: never[]) => "duplicate" | "exclusive" | null;
      }
    ) => {
      const model = signal({ target: "user" as ConditionalAccessTarget, actions });
      const tree = TestBed.runInInjectionContext(() =>
        form(model, (p) => applyActionRules(p.actions, p.target, service as never))
      );
      return { model, tree };
    };
    const kinds = (field: () => { errors(): { kind: string; message?: string }[] }) =>
      field()
        .errors()
        .map((error) => error.kind);
    const anyService = { actionsForTarget: () => [] as never[], actionConflict: () => null };

    it("accepts an action of a type the target allows", () => {
      const { tree } = rules([action("DENY")], { ...anyService, actionsForTarget: () => ["DENY"] as never[] });
      expect(kinds(tree.actions[0])).toEqual([]);
    });

    it("flags an action of a type the target does not allow", () => {
      const { tree } = rules([action("LOCK_USER", 60)], {
        ...anyService,
        actionsForTarget: () => ["DENY"] as never[]
      });
      expect(kinds(tree.actions[0])).toEqual([CA_ERR.stageActionNotAllowed]);
    });

    it("passes every action while the allowed types are not known yet", () => {
      const { tree } = rules([action("LOCK_USER", 60)], anyService);
      expect(kinds(tree.actions[0])).toEqual([]);
    });

    it("asks the service about the action at its own index and the target of the policy", () => {
      const actionConflict = jest.fn(() => null);
      const actions = [
        action("EMAIL_ADMIN", { subject: "s", body: "b" }),
        action("EMAIL_ADMIN", { subject: "s", body: "b" })
      ];
      const { model, tree } = rules(actions, { ...anyService, actionConflict });
      kinds(tree.actions[1]);
      expect(actionConflict).toHaveBeenCalledWith(model().actions, 1, "user");
    });

    it("flags a conflicting action with the message for its kind", () => {
      const { tree } = rules([action("DENY"), action("DENY")], { ...anyService, actionConflict: () => "duplicate" });
      expect(tree.actions[1]().errors()).toEqual([
        expect.objectContaining({ kind: CA_ERR.stageActionConflict, message: actionConflictMessage("duplicate") })
      ]);
    });

    it("flags an action without the value its type needs, with what is missing", () => {
      const { tree } = rules([action("LOCK_USER", null), action("DENY")], anyService);
      expect(kinds(tree.actions[0])).toEqual([CA_ERR.stageActionValue]);
      expect(tree.actions[0]().errors()[0].message).toEqual(expect.stringContaining("duration"));
      expect(kinds(tree.actions[1])).toEqual([]);
    });
  });

  describe("actionConflictMessage", () => {
    it("tells a duplicate from a contradiction", () => {
      expect(actionConflictMessage("duplicate")).toContain("already on this stage");
      expect(actionConflictMessage("exclusive")).toContain("contradicts");
    });
  });
});
