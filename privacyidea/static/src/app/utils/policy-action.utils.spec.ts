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
import type { PolicyActionDetail } from "@services/policies/policies.service";
import {
  actionNameWithoutExclusion,
  actionValueIsInvalid,
  boolActionValueEnablesAction,
  isExcludedActionName,
  withoutDisablingBoolActions
} from "./policy-action.utils";

describe("policy action utils", () => {
  it.each(["-policywrite", "!policywrite"])("treats %p as excluded action", (name) => {
    expect(isExcludedActionName(name)).toBe(true);
    expect(actionNameWithoutExclusion(name)).toBe("policywrite");
  });

  it.each(["policywrite", "*", "otppin"])("does not treat %p as excluded action", (name) => {
    expect(isExcludedActionName(name)).toBe(false);
    expect(actionNameWithoutExclusion(name)).toBe(name);
  });

  it.each([true, 1, "1", "True", "true", "TRUE", "", " ", null, undefined])(
    "takes the value %p as enabling a boolean action",
    (value) => {
      expect(boolActionValueEnablesAction(value)).toBe(true);
    }
  );

  it.each([false, 0, "0", "False", "false", "tRuE", "yes", "hotp"])(
    "takes the value %p as not enabling a boolean action",
    (value) => {
      expect(boolActionValueEnablesAction(value)).toBe(false);
    }
  );

  describe("actionValueIsInvalid", () => {
    it("takes a boolean action as invalid if its value does not enable it", () => {
      expect(actionValueIsInvalid({ type: "bool", desc: "" }, "hotp")).toBe(true);
      expect(actionValueIsInvalid({ type: "bool", desc: "" }, true)).toBe(false);
    });

    it.each(["abc", "1.5", "", 2.5])("takes the integer value %p as invalid", (value) => {
      expect(actionValueIsInvalid({ type: "int", desc: "" }, value)).toBe(true);
    });

    it.each(["7", 7, "-1"])("takes the integer value %p as valid", (value) => {
      expect(actionValueIsInvalid({ type: "int", desc: "" }, value)).toBe(false);
    });

    it("checks a value against the values of the definition", () => {
      const detail = { type: "str" as const, desc: "", value: ["userstore", "tokenpin", "none"] };
      expect(actionValueIsInvalid(detail, "userstore")).toBe(false);
      expect(actionValueIsInvalid(detail, "ldap")).toBe(true);
      // A number in the list matches its string form
      expect(actionValueIsInvalid({ type: "int", desc: "", value: [0, 1, 2] }, "1")).toBe(false);
    });

    it("checks every value of an action with several values", () => {
      const detail = {
        type: "str" as const,
        desc: "",
        multiple: true,
        value: ["ecdsa", "rsassa-pss", "rsassa-pkcs1v1_5"]
      };
      expect(actionValueIsInvalid(detail, "ecdsa  rsassa-pss")).toBe(false);
      expect(actionValueIsInvalid(detail, "ecdsa dsa")).toBe(true);
    });

    it("does not check against an empty list or a free text action", () => {
      expect(actionValueIsInvalid({ type: "str", desc: "", value: [] }, "realm1")).toBe(false);
      expect(actionValueIsInvalid({ type: "str", desc: "" }, "anything")).toBe(false);
      expect(actionValueIsInvalid({ type: "text", desc: "" }, "")).toBe(false);
    });
  });

  describe("withoutDisablingBoolActions", () => {
    const details: Record<string, PolicyActionDetail> = {
      triggerchallenge: { type: "bool", desc: "" },
      hotp_hashlib: { type: "str", desc: "", value: ["sha1", "sha256"] }
    };
    const detailOf = (name: string) => details[name] ?? null;

    it("leaves out a boolean action whose value does not enable it", () => {
      expect(withoutDisablingBoolActions({ triggerchallenge: "hotp", hotp_hashlib: "sha1" }, detailOf)).toEqual({
        hotp_hashlib: "sha1"
      });
    });

    it.each([true, "true", "1", ""])("keeps a boolean action with the enabling value %p", (value) => {
      expect(withoutDisablingBoolActions({ triggerchallenge: value }, detailOf)).toEqual({ triggerchallenge: value });
    });

    it("keeps excluded actions, actions of other types and unknown actions", () => {
      const actions = { "-triggerchallenge": "hotp", hotp_hashlib: "md5", unknown: "False" };
      expect(withoutDisablingBoolActions(actions, detailOf)).toEqual(actions);
    });
  });
});
