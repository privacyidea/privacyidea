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
import { tokenTypeDisplayDescription, tokenTypeDisplayLabel, tokenTypeLabel, tokenTypes } from "./token.utils";

describe("tokenTypeLabel", () => {
  it("returns the display name of a token type key", () => {
    expect(tokenTypeLabel("hotp")).toBe("HOTP");
    expect(tokenTypeLabel("4eyes")).toBe("4Eyes");
    expect(tokenTypeLabel("applspec")).toBe("Application Specific Password");
  });

  it("looks the key up case-insensitively", () => {
    expect(tokenTypeLabel("TOTP")).toBe("TOTP");
    expect(tokenTypeLabel("WebAuthn")).toBe("WebAuthn");
  });

  it("returns undefined for anything that is no token type", () => {
    expect(tokenTypeLabel("poll")).toBeUndefined();
    expect(tokenTypeLabel("")).toBeUndefined();
  });

  it("returns undefined for the members of Object.prototype", () => {
    expect(tokenTypeLabel("constructor")).toBeUndefined();
    expect(tokenTypeLabel("__proto__")).toBeUndefined();
    expect(tokenTypeLabel("toString")).toBeUndefined();
  });

  it("returns display names for token types that are no longer offered for enrollment", () => {
    expect(tokenTypeLabel("pw")).toBe("Static Password");
    expect(tokenTypeLabel("ocra")).toBe("OCRA");
    expect(tokenTypeLabel("daplug")).toBe("Daplug");
    expect(tokenTypeLabel("deprecated")).toBe("Deprecated");
    expect(tokenTypes.map((tokenType) => tokenType.key)).not.toContain("pw");
  });

  it("covers every token type", () => {
    expect(tokenTypes.filter((tokenType) => !tokenTypeLabel(tokenType.key))).toEqual([]);
  });
});

describe("tokenTypeDisplayLabel", () => {
  it("returns the part before the colon", () => {
    expect(tokenTypeDisplayLabel("HOTP: counter based", "fallback")).toBe("HOTP");
  });

  it("returns the fallback when the info has no colon", () => {
    expect(tokenTypeDisplayLabel("counter based", "fallback")).toBe("fallback");
  });

  it("returns the fallback for an empty info", () => {
    expect(tokenTypeDisplayLabel("", "fallback")).toBe("fallback");
  });

  it("returns an empty label for a leading colon", () => {
    expect(tokenTypeDisplayLabel(": desc", "fallback")).toBe("");
  });

  it("splits at the first colon only", () => {
    expect(tokenTypeDisplayLabel("Name: see http://x: more", "fallback")).toBe("Name");
  });
});

describe("tokenTypeDisplayDescription", () => {
  it("returns the trimmed part after the colon", () => {
    expect(tokenTypeDisplayDescription("Name:   some description ")).toBe("some description");
  });

  it("returns the whole text when the info has no colon", () => {
    expect(tokenTypeDisplayDescription("only a description")).toBe("only a description");
  });

  it("returns an empty string for an empty info", () => {
    expect(tokenTypeDisplayDescription("")).toBe("");
  });

  it("returns the description for a leading colon", () => {
    expect(tokenTypeDisplayDescription(": desc")).toBe("desc");
  });

  it("keeps a colon inside the description", () => {
    expect(tokenTypeDisplayDescription("Name: see http://x: more")).toBe("see http://x: more");
  });
});
