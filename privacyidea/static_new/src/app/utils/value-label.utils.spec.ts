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
    expect(valueDisplayLabel("1", ["0", "1"], "predicate")).toBe("Yes");
    expect(valueDisplayLabel(false, [false, true], "predicate")).toBe("No");
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
    expect(valueDisplayLabel("sha256", ["sha1", "sha256", "sha512"])).toBe("SHA-256");
    expect(valueDisplayLabel("tokenpin", ["tokenpin", "userstore", "none"])).toBe("Token PIN");
  });

  it("maps the container state disabled onto the deactivated label", () => {
    expect(valueDisplayLabel("disabled", ["active", "disabled", "lost", "damaged"])).toBe("Deactivated");
  });

  it("labels a value of a list the vocabulary covers completely", () => {
    expect(valueDisplayLabel("pending", ["clientwait", "pending", "enrolled"])).toBe("Pending");
    expect(valueDisplayLabel("none", ["tokenpin", "userstore", "none"])).toBe("None");
  });

  it("keeps every value of a list the vocabulary does not cover completely", () => {
    expect(valueDisplayLabel("pending", ["pending", "queued", "gone"])).toBe("pending");
    expect(valueDisplayLabel("clientwait", ["clientwait", "queued"])).toBe("clientwait");
  });

  it("keeps the names of a list the installation defines itself", () => {
    // Realm, resolver and server-configuration lists reach the value dropdowns as plain strings and
    // must never be relabeled - the admin has to recognize the name they created.
    expect(valueDisplayLabel("admin", ["admin", "defrealm"])).toBe("admin");
    expect(valueDisplayLabel("defrealm", ["admin", "defrealm"])).toBe("defrealm");
    expect(valueDisplayLabel("userstore", ["userstore", "myRadius"])).toBe("userstore");
    expect(valueDisplayLabels(["admin", "defrealm"])).toBeUndefined();
  });

  it("keeps a value that is not plain lower-case", () => {
    expect(valueDisplayLabel("Pending", ["clientwait", "Pending"])).toBe("Pending");
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

  it("maps token type keys of a list that also holds unknown types", () => {
    const backendValues = ["hotp", "totp", "pw", "ocra", "bogus"];
    expect(valueDisplayLabel("hotp", backendValues)).toBe("HOTP");
    expect(valueDisplayLabel("pw", backendValues)).toBe("Static Password");
    expect(valueDisplayLabel("ocra", backendValues)).toBe("OCRA");
    expect(valueDisplayLabel("bogus", backendValues)).toBe("bogus");
  });

  it("keeps values untouched when a single value is the only token type of the list", () => {
    expect(valueDisplayLabel("push", ["push", "poll"])).toBe("push");
  });

  it("prefers the token type name over the vocabulary in a token type list", () => {
    expect(valueDisplayLabel("yubikey", ["hotp", "totp", "yubikey"])).toBe("Yubikey AES Mode");
    expect(valueDisplayLabel("yubikey", ["generic", "smartphone", "yubikey"])).toBe("Yubikey");
  });

  const vocabularyLists: [string, string[], string[]][] = [
    ["remote_user", ["disable", "allowed", "force"], ["Disabled", "Allowed", "Forced"]],
    ["passkey login button", ["show", "hide"], ["Show", "Hide"]],
    ["logged in user", ["admin", "user"], ["Administrator", "User"]],
    ["script mode", ["background", "wait"], ["In background", "Wait"]],
    ["notification mimetype", ["plain", "html"], ["Plain text", "HTML"]],
    ["token application", ["ssh", "offline", "luks"], ["SSH", "Offline", "LUKS"]],
    ["container type", ["generic", "smartphone", "yubikey"], ["Generic", "Smartphone", "Yubikey"]],
    ["authentication", ["ACCEPT", "REJECT", "CHALLENGE", "DECLINED"], ["Accept", "Reject", "Challenge", "Declined"]],
    ["login mode", ["userstore", "privacyIDEA", "disable"], ["User store", "privacyIDEA", "Disabled"]]
  ];
  it.each(vocabularyLists)("labels every value of the %s list", (_name, values, expected) => {
    expect(values.map((value) => valueDisplayLabel(value, values))).toEqual(expected);
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
    expect(valueDisplayLabels([false, true], "predicate")).toEqual(["No", "Yes"]);
  });

  it("labels every value of the shared value lists", () => {
    expect(valueDisplayLabels(TOKEN_STATE_VALUES)).toEqual(["Active", "Deactivated", "Revoked", "Locked"]);
    expect(valueDisplayLabels(CONTAINER_STATE_VALUES)).toEqual(["Active", "Deactivated", "Lost", "Damaged"]);
    expect(valueDisplayLabels(AUTHENTICATION_VALUES)).toEqual(["Accept", "Challenge", "Reject", "Declined"]);
    expect(valueDisplayLabels(ROLLOUT_STATE_VALUES)).toEqual([
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
    expect(valueDisplayLabels(["clientwait", "Pending"])).toEqual(["Client wait", "Pending"]);
  });

  it("returns undefined when no value maps to a different label", () => {
    expect(valueDisplayLabels(["foo", "bar"])).toBeUndefined();
    expect(valueDisplayLabels([])).toBeUndefined();
    expect(valueDisplayLabels(undefined)).toBeUndefined();
  });
});
