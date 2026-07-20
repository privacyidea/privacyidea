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
import { filterColumnHint, filterMatchHint } from "./filter-hint.utils";

describe("filterMatchHint", () => {
  it("describes exact matching", () => {
    expect(filterMatchHint(true)).toContain("exact");
  });

  it("describes substring matching", () => {
    expect(filterMatchHint(false)).toContain("any part");
  });
});

describe("filterColumnHint", () => {
  it("shows the label and match mode with case for text keywords", () => {
    const hint = filterColumnHint("Serial", { exactMatch: false, caseSensitive: true, isBoolean: false });
    expect(hint).toContain("Filter by Serial");
    expect(hint).toContain("any part");
    expect(hint).toContain("Case-sensitive.");
  });

  it("marks case-insensitive text keywords", () => {
    const hint = filterColumnHint("Description", { exactMatch: false, caseSensitive: false, isBoolean: false });
    expect(hint).toContain("Case-insensitive.");
  });

  it("describes boolean keywords as true/false and omits match/case", () => {
    const hint = filterColumnHint("Active", { exactMatch: false, caseSensitive: false, isBoolean: true });
    expect(hint).toContain("true or false");
    expect(hint).not.toContain("Case-");
    expect(hint).not.toContain("any part");
  });
});
