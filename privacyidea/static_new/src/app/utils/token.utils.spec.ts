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
import { tokenTypeLabel, tokenTypes } from "./token.utils";

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
