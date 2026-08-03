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
import { FilterValue } from "./filter_value";

describe("FilterValue parsing", () => {
  test("parses dots in values (no truncation at .)", () => {
    const fv = new FilterValue({ value: "description: v1.2" });
    expect(fv.filterMap.get("description")).toBe("v1.2");
  });

  test("captures multi-word unquoted value up to the next key", () => {
    const fv = new FilterValue({ value: "description: this token is user: alice" });
    expect(fv.filterMap.get("description")).toBe("this token is");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("supports double-quoted phrases", () => {
    const fv = new FilterValue({ value: `description:"this token was created remotely" user:alice` });
    expect(fv.filterMap.get("description")).toBe("this token was created remotely");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("supports single-quoted phrases", () => {
    const fv = new FilterValue({ value: `description:'this token is unused' user:alice` });
    expect(fv.filterMap.get("description")).toBe("this token is unused");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("does not swallow the next key when previous value is empty (serial: description: test)", () => {
    const fv = new FilterValue({ value: "serial: description: test" });
    expect(fv.filterMap.get("serial")).toBe("");
    expect(fv.filterMap.get("description")).toBe("test");
  });

  test("allows empty values explicitly (serial:)", () => {
    const fv = new FilterValue({ value: "serial:" });
    expect(fv.filterMap.get("serial")).toBe("");
  });

  test("multiple pairs with punctuation and spaces", () => {
    const fv = new FilterValue({
      value: `description:"v1.2 release - final" user: bob@example.com realm:"engineering team"`
    });
    expect(fv.filterMap.get("description")).toBe("v1.2 release - final");
    expect(fv.filterMap.get("user")).toBe("bob@example.com");
    expect(fv.filterMap.get("realm")).toBe("engineering team");
  });

  test("hiddenFilterMap mirrors parsing rules", () => {
    const fv = new FilterValue({ hiddenValue: `serial: ABC.123 description:"hidden stuff"` });
    expect(fv.hiddenFilterMap.get("serial")).toBe("ABC.123");
    expect(fv.hiddenFilterMap.get("description")).toBe("hidden stuff");
  });
});

describe("FilterValue helpers", () => {
  test("addKey inserts key once and hasKey detects it", () => {
    let fv = new FilterValue();
    fv = fv.addKey("serial");
    expect(fv.value).toBe("serial: ");
    fv = fv.addKey("serial");
    expect(fv.value).toBe("serial: ");
    expect(fv.hasKey("serial")).toBe(true);
  });

  test("removeKey removes the whole segment of that key only", () => {
    let fv = new FilterValue({ value: `serial: description:"this token is" user: alice` });
    fv = fv.removeKey("description");
    expect(fv.filterMap.get("description")).toBeUndefined();
    expect(fv.filterMap.get("serial")).toBe("");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("addHiddenKey / removeHiddenKey behave like visible counterparts", () => {
    let fv = new FilterValue({ hiddenValue: "" });
    fv = fv.addHiddenKey("container_serial");
    expect(fv.hiddenFilterMap.get("container_serial")).toBe("");
    fv = fv.removeHiddenKey("container_serial");
    expect(fv.hiddenFilterMap.get("container_serial")).toBeUndefined();
  });

  test("addEntry updates value for a key", () => {
    let fv = new FilterValue({ value: "description:" });
    fv = fv.addEntry("description", "this token is");
    expect(fv.filterMap.get("description")).toBe("this token is");
  });

  test("value, hiddenValue, isEmpty and isNotEmpty reflect the visible value", () => {
    const empty = new FilterValue({ hiddenValue: "container_serial: CONT0001" });
    expect(empty.value).toBe("");
    expect(empty.filterString).toBe("");
    expect(empty.hiddenValue).toBe("container_serial: CONT0001");
    expect(empty.isEmpty).toBe(true);
    expect(empty.isNotEmpty).toBe(false);

    const filled = new FilterValue({ value: "user: alice" });
    expect(filled.isEmpty).toBe(false);
    expect(filled.isNotEmpty).toBe(true);
  });

  test("setString replaces the visible value", () => {
    const fv = new FilterValue({ value: "user: alice" });
    fv.setString = "serial: OATH0001";
    expect(fv.value).toBe("serial: OATH0001");
    expect(fv.filterMap.get("user")).toBeUndefined();
    expect(fv.filterMap.get("serial")).toBe("OATH0001");
  });

  test("getValueOfKey returns the value of a visible key only", () => {
    const fv = new FilterValue({ value: "user: alice", hiddenValue: "container_serial: CONT0001" });
    expect(fv.getValueOfKey("user")).toBe("alice");
    expect(fv.getValueOfKey("container_serial")).toBeUndefined();
    expect(fv.getValueOfKey("serial")).toBeUndefined();
  });

  test("allEntries lists the visible entries before the hidden ones", () => {
    const fv = new FilterValue({ value: "user: alice serial: OATH", hiddenValue: "serial: HIDDEN0001" });
    expect(fv.allEntries).toEqual([
      ["user", "alice"],
      ["serial", "OATH"],
      ["serial", "HIDDEN0001"]
    ]);
    expect(new Map(fv.allEntries).get("serial")).toBe("HIDDEN0001");
  });

  test("booleanValueOfKey reads true and false, and undefined for anything else", () => {
    expect(new FilterValue({ value: "active: true" }).booleanValueOfKey("active")).toBe(true);
    expect(new FilterValue({ value: "active: TRUE" }).booleanValueOfKey("active")).toBe(true);
    expect(new FilterValue({ value: "active: false" }).booleanValueOfKey("active")).toBe(false);
    expect(new FilterValue({ value: "active: False" }).booleanValueOfKey("active")).toBe(false);
    expect(new FilterValue({ value: "active: yes" }).booleanValueOfKey("active")).toBeUndefined();
    expect(new FilterValue({ value: "active:" }).booleanValueOfKey("active")).toBeUndefined();
    expect(new FilterValue({ value: "user: alice" }).booleanValueOfKey("active")).toBeUndefined();
  });

  test("toggleKey adds a missing key and removes an existing one", () => {
    let fv = new FilterValue({ value: "user: alice" });
    fv = fv.toggleKey("serial");
    expect(fv.hasKey("serial")).toBe(true);
    fv = fv.toggleKey("serial");
    expect(fv.hasKey("serial")).toBe(false);
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("toggleKeys toggles every key of the list", () => {
    let fv = new FilterValue({ value: "serial: " });
    fv = fv.toggleKeys(["serial", "user"]);
    expect(fv.hasKey("serial")).toBe(false);
    expect(fv.hasKey("user")).toBe(true);
  });

  test("toggleBooleanKey cycles through true, false and not filtered", () => {
    let fv = new FilterValue({ value: "user: alice" });

    fv = fv.toggleBooleanKey("active");
    expect(fv.getValueOfKey("active")).toBe("true");

    fv = fv.toggleBooleanKey("active");
    expect(fv.getValueOfKey("active")).toBe("false");

    fv = fv.toggleBooleanKey("active");
    expect(fv.hasKey("active")).toBe(false);
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("toggleBooleanKey restarts the cycle for a value that is not a boolean", () => {
    const fv = new FilterValue({ value: "active: maybe" }).toggleBooleanKey("active");
    expect(fv.getValueOfKey("active")).toBe("true");
  });

  test("updateHiddenEntry adds and updates a hidden entry without touching the visible value", () => {
    let fv = new FilterValue({ value: "user: alice" });

    fv = fv.updateHiddenEntry("container_serial", "CONT0001");
    expect(fv.hiddenFilterMap.get("container_serial")).toBe("CONT0001");

    fv = fv.updateHiddenEntry("container_serial", "CONT0002");
    expect(fv.hiddenFilterMap.get("container_serial")).toBe("CONT0002");
    expect(fv.value).toBe("user: alice");
  });

  test("setHiddenFromMap replaces all hidden entries", () => {
    const fv = new FilterValue({ hiddenValue: "container_serial: CONT0001" });

    fv.setHiddenFromMap(
      new Map([
        ["serial", "OATH0001"],
        ["realm", "defrealm"]
      ])
    );

    expect(fv.hiddenFilterMap.get("container_serial")).toBeUndefined();
    expect(fv.hiddenFilterMap.get("serial")).toBe("OATH0001");
    expect(fv.hiddenFilterMap.get("realm")).toBe("defrealm");
  });
});

describe("FilterValue keyword parsing alongside free text", () => {
  test("does not let leading free text affect the keyword filterMap", () => {
    const fv = new FilterValue({ value: "root username: admin" });
    expect(fv.filterMap.get("username")).toBe("admin");
  });
});

describe("Round-trip safety via setFromMap", () => {
  test("map -> setFromMap -> parse yields the same key/values (handles spaces and dots)", () => {
    const source = new Map<string, string>([
      ["description", "this token is unused"],
      ["user", "bob@example.com"],
      ["version", "v1.2.3"]
    ]);

    const fv = new FilterValue();
    fv.setFromMap(source);

    const parsed = fv.filterMap;
    expect(parsed.get("description")).toBe("this token is unused");
    expect(parsed.get("user")).toBe("bob@example.com");
    expect(parsed.get("version")).toBe("v1.2.3");
  });

  test("round-trip with empty values preserved", () => {
    const source = new Map<string, string>([
      ["serial", ""],
      ["description", ""],
      ["user", "alice"]
    ]);

    const fv = new FilterValue();
    fv.setFromMap(source);

    const parsed = fv.filterMap;
    expect(parsed.get("serial")).toBe("");
    expect(parsed.get("description")).toBe("");
    expect(parsed.get("user")).toBe("alice");
  });
});

describe("Edge cases", () => {
  test("trailing spaces do not affect parsing", () => {
    const fv = new FilterValue({ value: "description:\"this token is\"   user:  alice   " });
    expect(fv.filterMap.get("description")).toBe("this token is");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("values with quotes inside are preserved via setFromMap (escaped by serializer)", () => {
    const source = new Map<string, string>([
      ["description", `He said "hello"`],
      ["note", "it's fine"]
    ]);
    const fv = new FilterValue();
    fv.setFromMap(source);
    const parsed = fv.filterMap;
    expect(parsed.get("description")).toBe(`He said "hello"`);
    expect(parsed.get("note")).toBe("it's fine");
  });

  test("excludes asterisk-only values (wildcard means no filter)", () => {
    const fv = new FilterValue({
      value: `description:* user:alice version:"*" note:'*' realm:"**"`
    });

    expect(fv.filterMap.get("description")).toBeUndefined();
    expect(fv.filterMap.get("version")).toBeUndefined();
    expect(fv.filterMap.get("note")).toBeUndefined();

    expect(fv.filterMap.get("user")).toBe("alice");

    expect(fv.filterMap.get("realm")).toBe("**");

    const fvh = new FilterValue({
      hiddenValue: `serial:* container_serial:'*' keep:**`
    });
    expect(fvh.hiddenFilterMap.get("serial")).toBeUndefined();
    expect(fvh.hiddenFilterMap.get("container_serial")).toBeUndefined();
    expect(fvh.hiddenFilterMap.get("keep")).toBe("**");
  });

  test("setFromMap drops asterisk-only values", () => {
    const source = new Map<string, string>([
      ["description", "*"],
      ["user", "alice"]
    ]);
    const fv = new FilterValue();
    fv.setFromMap(source);
    expect(fv.filterMap.get("description")).toBeUndefined();
    expect(fv.filterMap.get("user")).toBe("alice");
  });
});
