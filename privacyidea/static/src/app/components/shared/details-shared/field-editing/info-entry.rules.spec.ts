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
import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { form } from "@angular/forms/signals";
import { InfoEntry, INFO_KEY_EXISTS, infoEntryRules } from "./info-entry.rules";

describe("infoEntryRules", () => {
  const existing = signal<string[]>(["a", "b"]);

  function createForm(entry: InfoEntry) {
    const model = signal(entry);
    const tree = TestBed.runInInjectionContext(() => form(model, (p) => infoEntryRules(p, existing)));
    return { model, tree };
  }

  const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((e) => e.kind);

  it("accepts an empty row", () => {
    const { tree } = createForm({ key: "", value: "" });
    expect(tree().valid()).toBe(true);
  });

  it("treats whitespace in both inputs as an empty row", () => {
    const { tree } = createForm({ key: "  ", value: " " });
    expect(tree().valid()).toBe(true);
  });

  it("requires the key once a value is given", () => {
    const { tree } = createForm({ key: "", value: "x" });
    expect(kinds(tree.key())).toEqual(["required"]);
    expect(kinds(tree.value())).toEqual([]);
  });

  it("requires the value once a key is given", () => {
    const { tree } = createForm({ key: "c", value: "  " });
    expect(kinds(tree.value())).toEqual(["required"]);
    expect(kinds(tree.key())).toEqual([]);
  });

  it("accepts a new key with a value", () => {
    const { tree } = createForm({ key: "c", value: "x" });
    expect(tree().valid()).toBe(true);
  });

  it("rejects a key that already exists, also with surrounding whitespace", () => {
    expect(kinds(createForm({ key: "a", value: "x" }).tree.key())).toEqual([INFO_KEY_EXISTS]);
    expect(kinds(createForm({ key: " b ", value: "x" }).tree.key())).toEqual([INFO_KEY_EXISTS]);
  });

  it("follows the keys that exist and the typed values", () => {
    const { model, tree } = createForm({ key: "c", value: "x" });
    expect(tree().valid()).toBe(true);

    existing.set(["a", "b", "c"]);
    expect(kinds(tree.key())).toEqual([INFO_KEY_EXISTS]);
    existing.set(["a", "b"]);

    model.set({ key: "c", value: "" });
    expect(kinds(tree.value())).toEqual(["required"]);
  });
});
