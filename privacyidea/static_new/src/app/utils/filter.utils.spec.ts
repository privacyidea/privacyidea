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
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  buildFilterParams,
  filterParamsEqual,
  toBooleanParam,
  toWildcardParam,
  withDefaultRealm
} from "./filter.utils";

describe("filterParamsEqual", () => {
  it("reports equality for the same keys and values", () => {
    expect(filterParamsEqual({ serial: "*OATH*", user: "*alice*" }, { user: "*alice*", serial: "*OATH*" })).toBe(true);
  });

  it("reports a difference when a value changed", () => {
    expect(filterParamsEqual({ serial: "*OATH*" }, { serial: "*OATH1*" })).toBe(false);
  });

  it("reports a difference when a key is missing on either side", () => {
    expect(filterParamsEqual({ serial: "*OATH*" }, { serial: "*OATH*", user: "*alice*" })).toBe(false);
    expect(filterParamsEqual({ serial: "*OATH*", user: "*alice*" }, { serial: "*OATH*" })).toBe(false);
  });

  it("reports a difference when the keys differ but their count does not", () => {
    expect(filterParamsEqual({ serial: "*OATH*" }, { user: "*OATH*" })).toBe(false);
  });

  it("reports equality for two empty records", () => {
    expect(filterParamsEqual({}, {})).toBe(true);
  });
});

describe("toWildcardParam", () => {
  it("wraps the value in wildcards", () => {
    expect(toWildcardParam("serial", "OATH", new Set())).toEqual({ serial: "*OATH*" });
  });

  it("keeps the value as it is for a key the backend matches exactly", () => {
    expect(toWildcardParam("type", "hotp", new Set(["type"]))).toEqual({ type: "hotp" });
  });

  it("trims the value", () => {
    expect(toWildcardParam("serial", "  OATH  ", new Set())).toEqual({ serial: "*OATH*" });
  });

  it("yields no parameter for an empty, blank, missing or wildcard-only value", () => {
    expect(toWildcardParam("serial", "", new Set())).toEqual({});
    expect(toWildcardParam("serial", "   ", new Set())).toEqual({});
    expect(toWildcardParam("serial", null, new Set())).toEqual({});
    expect(toWildcardParam("serial", undefined, new Set())).toEqual({});
    expect(toWildcardParam("serial", "**", new Set())).toEqual({});
  });
});

describe("buildFilterParams", () => {
  it("keeps the allowed keys and skips the unknown ones", () => {
    const entries: [string, string][] = [
      ["serial", "OATH"],
      ["unknown", "value"]
    ];

    expect(buildFilterParams(entries, ["serial"])).toEqual({ serial: "*OATH*" });
  });

  it("skips the values the backend cannot use", () => {
    const entries: [string, string | null][] = [
      ["serial", "OATH"],
      ["user", ""],
      ["realm", null]
    ];

    expect(buildFilterParams(entries, ["serial", "user", "realm"])).toEqual({ serial: "*OATH*" });
  });

  it("does not wrap the exactly matched keys in wildcards", () => {
    const entries: [string, string][] = [
      ["serial", "OATH"],
      ["type", "hotp"]
    ];

    expect(buildFilterParams(entries, ["serial", "type"], new Set(["type"]))).toEqual({
      serial: "*OATH*",
      type: "hotp"
    });
  });

  it("accepts the entries of a filter map", () => {
    const filter = new FilterValue({ value: "serial: OATH user: alice" });

    expect(buildFilterParams(filter.filterMap, ["serial", "user"])).toEqual({
      serial: "*OATH*",
      user: "*alice*"
    });
  });
});

describe("toBooleanParam", () => {
  it("spells out a true value", () => {
    expect(toBooleanParam("true")).toBe("True");
    expect(toBooleanParam("TRUE")).toBe("True");
    expect(toBooleanParam("1")).toBe("True");
  });

  it("spells out a false value", () => {
    expect(toBooleanParam("false")).toBe("False");
    expect(toBooleanParam("False")).toBe("False");
    expect(toBooleanParam("0")).toBe("False");
  });

  it("yields undefined for a value that does not read as a boolean", () => {
    expect(toBooleanParam("")).toBeUndefined();
    expect(toBooleanParam("yes")).toBeUndefined();
    expect(toBooleanParam("2")).toBeUndefined();
  });
});

describe("withDefaultRealm", () => {
  it("adds the realm to a filter that names a user", () => {
    const filter = new FilterValue({ value: "user: alice" });

    expect(withDefaultRealm(filter, "defrealm").getValueOfKey("realm")).toBe("defrealm");
  });

  it("keeps a filter that already names a realm", () => {
    const filter = new FilterValue({ value: "user: alice realm: otherrealm" });

    expect(withDefaultRealm(filter, "defrealm").getValueOfKey("realm")).toBe("otherrealm");
  });

  it("keeps a filter without a user", () => {
    const filter = new FilterValue({ value: "serial: OATH" });

    expect(withDefaultRealm(filter, "defrealm").hasKey("realm")).toBe(false);
  });

  it("keeps the filter when there is no default realm", () => {
    const filter = new FilterValue({ value: "user: alice" });

    expect(withDefaultRealm(filter, "").hasKey("realm")).toBe(false);
  });
});
