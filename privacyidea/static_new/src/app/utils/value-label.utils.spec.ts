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
  AUTHENTICATION_VALUES,
  booleanDisplayLabel,
  CONTAINER_STATE_VALUES,
  ROLLOUT_STATE_VALUES,
  TOKEN_STATE_VALUES,
  valueDisplayLabel,
  valueDisplayLabels
} from "./value-label.utils";

describe("valueDisplayLabel", () => {
  it("maps a numeric pair to the switch labels", () => {
    expect(valueDisplayLabel("1", ["0", "1"])).toBe("On");
    expect(valueDisplayLabel("0", ["0", "1"])).toBe("Off");
  });

  it("maps a boolean pair regardless of the value type and casing", () => {
    expect(valueDisplayLabel(true, [false, true])).toBe("On");
    expect(valueDisplayLabel("TRUE", ["false", "true"])).toBe("On");
    expect(valueDisplayLabel("False", ["false", "true"])).toBe("Off");
  });

  it("maps a pair to yes/no with the predicate preset", () => {
    expect(valueDisplayLabel("1", ["0", "1"], { preset: "predicate" })).toBe("Yes");
    expect(valueDisplayLabel(false, [false, true], { preset: "predicate" })).toBe("No");
  });

  it("recognizes a pair independently of the order of the allowed values", () => {
    expect(valueDisplayLabel("1", ["1", "0"])).toBe("On");
  });

  it("does not treat a list of more than two values as a pair", () => {
    expect(valueDisplayLabel("1", ["0", "1", "2"])).toBe("1");
  });

  it("returns the raw value when it is not one of the allowed values", () => {
    expect(valueDisplayLabel("2", ["0", "1"])).toBe("2");
    expect(valueDisplayLabel("sha384", ["sha1", "sha256", "sha512"])).toBe("sha384");
  });

  it("returns the raw value when there are no allowed values", () => {
    expect(valueDisplayLabel("sha256", undefined)).toBe("sha256");
    expect(valueDisplayLabel("sha256", [])).toBe("sha256");
  });

  it("returns an empty string for a missing value", () => {
    expect(valueDisplayLabel(undefined, ["0", "1"])).toBe("");
  });

  it("maps a known vocabulary value to its display label", () => {
    expect(valueDisplayLabel("sha256", ["sha1", "sha256", "sha512"], { vocabulary: true })).toBe("SHA-256");
    expect(valueDisplayLabel("tokenpin", ["tokenpin", "userstore", "none"], { vocabulary: true })).toBe("Token PIN");
  });

  it("maps the container state disabled onto the deactivated label", () => {
    expect(valueDisplayLabel("disabled", ["active", "disabled", "lost", "damaged"], { vocabulary: true })).toBe(
      "Deactivated"
    );
  });

  it("labels a value of a list the vocabulary covers completely", () => {
    expect(valueDisplayLabel("pending", ["clientwait", "pending", "enrolled"], { vocabulary: true })).toBe("Pending");
    expect(valueDisplayLabel("none", ["tokenpin", "userstore", "none"], { vocabulary: true })).toBe("None");
  });

  it("keeps every value of a list the vocabulary does not cover completely", () => {
    expect(valueDisplayLabel("pending", ["pending", "queued", "gone"], { vocabulary: true })).toBe("pending");
    expect(valueDisplayLabel("clientwait", ["clientwait", "queued"], { vocabulary: true })).toBe("clientwait");
  });

  it("keeps the names of a list the installation defines itself", () => {
    // Realm, resolver, token group and server-configuration lists reach the value dropdowns as
    // plain strings and must never be relabeled - the admin has to recognize the name they created.
    expect(valueDisplayLabel("admin", ["admin", "defrealm"])).toBe("admin");
    expect(valueDisplayLabel("defrealm", ["admin", "defrealm"])).toBe("defrealm");
    expect(valueDisplayLabel("userstore", ["userstore", "myRadius"])).toBe("userstore");
    expect(valueDisplayLabels(["admin", "defrealm"])).toBeUndefined();
  });

  it("keeps names that happen to be spelled like vocabulary values", () => {
    // The values alone do not say where a list comes from, so the vocabulary stays off unless the
    // caller vouches for its list. Realms called "active"/"verify" or token groups called
    // "locked"/"lost" are ordinary names, not a closed vocabulary.
    expect(valueDisplayLabels(["active", "verify"])).toBeUndefined();
    expect(valueDisplayLabels(["locked", "lost"])).toBeUndefined();
    expect(valueDisplayLabels(["userstore", "none"])).toBeUndefined();
    expect(valueDisplayLabel("active", ["active", "verify"])).toBe("active");
  });

  it("labels the same list once the caller vouches for it", () => {
    expect(valueDisplayLabels(["active", "verify"], { vocabulary: true })).toEqual(["Active", "Verify"]);
  });

  it("keeps a value that is not plain lower-case", () => {
    expect(valueDisplayLabel("Pending", ["clientwait", "Pending"], { vocabulary: true })).toBe("Pending");
  });

  it("maps token type keys to their display names when the list holds nothing else", () => {
    const tokenTypeValues = ["hotp", "totp", "motp", "sshkey"];
    expect(valueDisplayLabel("hotp", tokenTypeValues)).toBe("HOTP");
    expect(valueDisplayLabel("totp", tokenTypeValues)).toBe("TOTP");
    expect(valueDisplayLabel("motp", tokenTypeValues)).toBe("mOTP");
    expect(valueDisplayLabel("sshkey", tokenTypeValues)).toBe("SSH Key");
  });

  it("maps token type keys in a two-value list without mistaking it for a pair", () => {
    expect(valueDisplayLabel("hotp", ["hotp", "totp"])).toBe("HOTP");
  });

  it("maps the token types that are no longer offered for enrollment", () => {
    const backendValues = ["hotp", "totp", "pw", "ocra"];
    expect(valueDisplayLabel("pw", backendValues)).toBe("Static Password");
    expect(valueDisplayLabel("ocra", backendValues)).toBe("OCRA");
  });

  it("keeps every value of a list that holds something else than token types", () => {
    // One unknown value is enough: the list is then a list of names the installation chose, or a
    // token type this frontend does not know, and either way renaming its neighbours is wrong.
    const mixedValues = ["hotp", "totp", "bogus"];
    expect(valueDisplayLabel("hotp", mixedValues)).toBe("hotp");
    expect(valueDisplayLabel("bogus", mixedValues)).toBe("bogus");
    expect(valueDisplayLabels(mixedValues)).toBeUndefined();
  });

  it("keeps the names of realms that are spelled like token types", () => {
    // Two realms called "email" and "sms" are named by the installation, not a token type list.
    expect(valueDisplayLabels(["email", "sms", "corporate"])).toBeUndefined();
    expect(valueDisplayLabel("email", ["email", "sms", "corporate"])).toBe("email");
  });

  it("keeps values untouched when a single value is the only token type of the list", () => {
    expect(valueDisplayLabel("push", ["push", "poll"])).toBe("push");
  });

  it("keeps the members of Object.prototype out of both label sources", () => {
    expect(valueDisplayLabel("constructor", ["constructor", "__proto__"], { vocabulary: true })).toBe("constructor");
    expect(valueDisplayLabel("hotp", ["hotp", "constructor"])).toBe("hotp");
    expect(valueDisplayLabels(["toString", "valueOf"], { vocabulary: true })).toBeUndefined();
  });

  // Every list an opted-in call site can hand in: the four shared constant lists are covered in the
  // valueDisplayLabels suite, these are the value lists of POLICY_VOCABULARY_ACTIONS and the audit
  // authentication column. A value the vocabulary misses would leave its whole list unlabeled.
  const vocabularyLists: [string, string[], string[]][] = [
    ["autoassignment", ["any_pin", "userstore"], ["Any PIN", "User store"]],
    ["hashlib", ["sha1", "sha256", "sha512"], ["SHA-1", "SHA-256", "SHA-512"]],
    ["login_mode", ["userstore", "privacyIDEA", "disable"], ["User store", "privacyIDEA", "Disabled"]],
    ["otppin", ["tokenpin", "userstore", "none"], ["Token PIN", "User store", "None"]],
    ["remote_user", ["disable", "allowed", "force"], ["Disabled", "Allowed", "Forced"]],
    ["timeout_action", ["logout", "lockscreen"], ["Logout", "Lock screen"]],
    ["authentication", ["ACCEPT", "REJECT", "CHALLENGE", "DECLINED"], ["Accept", "Reject", "Challenge", "Declined"]]
  ];
  it.each(vocabularyLists)("labels every value of the %s list", (_name, values, expected) => {
    expect(values.map((value) => valueDisplayLabel(value, values, { vocabulary: true }))).toEqual(expected);
  });
});

describe("booleanDisplayLabel", () => {
  it("maps booleans and their numeric spellings to the switch labels", () => {
    expect(booleanDisplayLabel(true)).toBe("On");
    expect(booleanDisplayLabel(false)).toBe("Off");
    expect(booleanDisplayLabel(1)).toBe("On");
    expect(booleanDisplayLabel("0")).toBe("Off");
  });

  it("maps to yes/no with the predicate preset", () => {
    expect(booleanDisplayLabel(true, "predicate")).toBe("Yes");
    expect(booleanDisplayLabel("0", "predicate")).toBe("No");
  });

  it("returns an empty string for empty, null and undefined values", () => {
    expect(booleanDisplayLabel("")).toBe("");
    expect(booleanDisplayLabel(null)).toBe("");
    expect(booleanDisplayLabel(undefined)).toBe("");
  });

  it("returns the raw value for anything that is not a known boolean", () => {
    expect(booleanDisplayLabel("maybe")).toBe("maybe");
    expect(booleanDisplayLabel(7)).toBe("7");
  });
});

describe("valueDisplayLabels", () => {
  it("labels every value of a pair", () => {
    expect(valueDisplayLabels(["0", "1"])).toEqual(["Off", "On"]);
    expect(valueDisplayLabels([false, true], { preset: "predicate" })).toEqual(["No", "Yes"]);
  });

  it("labels every value of the shared value lists", () => {
    const vocab = { vocabulary: true };
    expect(valueDisplayLabels(TOKEN_STATE_VALUES, vocab)).toEqual(["Active", "Deactivated", "Revoked", "Locked"]);
    expect(valueDisplayLabels(CONTAINER_STATE_VALUES, vocab)).toEqual(["Active", "Deactivated", "Lost", "Damaged"]);
    expect(valueDisplayLabels(AUTHENTICATION_VALUES, vocab)).toEqual(["Accept", "Challenge", "Reject", "Declined"]);
    expect(valueDisplayLabels(ROLLOUT_STATE_VALUES, vocab)).toEqual([
      "Client wait",
      "Pending",
      "Verify",
      "Enrolled",
      "Broken",
      "Failed",
      "Denied"
    ]);
  });

  it("labels every token type key of a token type list", () => {
    expect(valueDisplayLabels(["hotp", "totp", "webauthn"])).toEqual(["HOTP", "TOTP", "WebAuthn"]);
  });

  it("labels a list whose values differ in casing", () => {
    expect(valueDisplayLabels(["clientwait", "Pending"], { vocabulary: true })).toEqual(["Client wait", "Pending"]);
  });

  it("returns undefined when no value maps to a different label", () => {
    expect(valueDisplayLabels(["foo", "bar"])).toBeUndefined();
    expect(valueDisplayLabels([])).toBeUndefined();
    expect(valueDisplayLabels(undefined)).toBeUndefined();
  });
});
