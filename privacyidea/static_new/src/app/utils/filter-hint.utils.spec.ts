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
import { filterColumnHint, filterInputHint, filterKeywordHint } from "./filter-hint.utils";

describe("filterInputHint", () => {
  it("only states what the placeholder does not already show", () => {
    expect(filterInputHint()).toBe(
      'Quote values with spaces or colons: description: "note: 2fa"\nWildcard: * where partial match is supported\nCase-insensitive'
    );
  });

  it("hedges the case note where the backend does not normalise case", () => {
    expect(filterInputHint({ mayBeCaseSensitive: true })).toBe(
      'Quote values with spaces or colons: description: "note: 2fa"\nWildcard: * where partial match is supported\nMostly case-insensitive'
    );
  });
});

describe("filterKeywordHint", () => {
  it("lists the accepted keywords", () => {
    expect(filterKeywordHint(["serial", "type"])).toBe("Keywords: serial, type");
  });

  it("stays empty without keywords", () => {
    expect(filterKeywordHint([])).toBe("");
  });
});

describe("filterColumnHint", () => {
  it("names partial matching where the value is wrapped in wildcards", () => {
    expect(filterColumnHint("Description", { exactMatch: false, isBoolean: false })).toBe(
      "Filter by Description\npartial match"
    );
  });

  it("names exact matching only where it applies", () => {
    expect(filterColumnHint("Realm", { exactMatch: true, isBoolean: false })).toBe("Filter by Realm\nexact match");
  });

  it("hedges keywords the database decides on", () => {
    expect(filterColumnHint("Serial", { exactMatch: false, isBoolean: false, caseNote: "usually-insensitive" })).toBe(
      "Filter by Serial\npartial match, usually case-insensitive"
    );
  });

  it("warns about keywords that are usually case-sensitive", () => {
    expect(filterColumnHint("infokey", { exactMatch: true, isBoolean: false, caseNote: "usually-sensitive" })).toBe(
      "Filter by infokey\nexact match, usually case-sensitive"
    );
  });

  it("states plain case sensitivity", () => {
    expect(filterColumnHint("x", { exactMatch: false, isBoolean: false, caseNote: "sensitive" })).toBe(
      "Filter by x\npartial match, case-sensitive"
    );
  });

  it("describes boolean keywords as true/false only", () => {
    expect(filterColumnHint("Active", { exactMatch: false, isBoolean: true })).toBe("Filter by Active\ntrue or false");
  });

});
