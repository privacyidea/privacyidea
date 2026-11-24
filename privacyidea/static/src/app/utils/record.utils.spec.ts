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
import { recordsEqual } from "./record.utils";

describe("recordsEqual", () => {
  it("is true for the same keys and values in any order", () => {
    expect(recordsEqual({ a: "1", b: "2" }, { b: "2", a: "1" })).toBe(true);
    expect(recordsEqual({}, {})).toBe(true);
  });

  it("is false for a different value, a missing key and an extra key", () => {
    expect(recordsEqual<Record<string, string>>({ a: "2" }, { a: "1" })).toBe(false);
    expect(recordsEqual<Record<string, string>>({ a: "1" }, { a: "1", b: "2" })).toBe(false);
    expect(recordsEqual<Record<string, string>>({ a: "1", b: "2" }, { a: "1" })).toBe(false);
  });

  it("tells an absent key from a key that holds undefined", () => {
    expect(recordsEqual<Record<string, string | undefined>>({ a: undefined }, { b: undefined })).toBe(false);
  });

  it("compares the values by identity, not by content", () => {
    expect(recordsEqual({ a: [1] }, { a: [1] })).toBe(false);
  });
});
