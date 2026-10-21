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
import {
  ERR,
  EVENT_NAME_PATTERN,
  IDENTIFIER_PATTERN,
  RESOLVER_RESERVED_NAMES,
  identifierName,
  mustEqual,
  requiredNonBlank,
  requiredNonEmptyArray,
  reservedNames
} from "./form-rules.utils";
import { reservedNames as reservedNamesSource } from "./reserved-names.utils";

describe("form-rules.utils", () => {
  const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((e) => e.kind);

  describe("patterns and constants", () => {
    it.each(["abc", "A.b-c_1", "..", ""])("IDENTIFIER_PATTERN accepts %p", (name) => {
      expect(IDENTIFIER_PATTERN.test(name)).toBe(true);
    });

    it.each(["a b", "a/b", "ä", "a@b"])("IDENTIFIER_PATTERN rejects %p", (name) => {
      expect(IDENTIFIER_PATTERN.test(name)).toBe(false);
    });

    it("EVENT_NAME_PATTERN additionally accepts the space", () => {
      expect(EVENT_NAME_PATTERN.test("my event.1")).toBe(true);
      expect(EVENT_NAME_PATTERN.test("my/event")).toBe(false);
    });

    it("reserves test and the dot segments for resolvers", () => {
      expect([...RESOLVER_RESERVED_NAMES]).toEqual(["test", ".", ".."]);
    });

    it("re-exports reservedNames", () => {
      expect(reservedNames).toBe(reservedNamesSource);
    });

    it("keeps the kinds the templates read", () => {
      expect(ERR).toEqual(
        expect.objectContaining({
          required: "required",
          pattern: "pattern",
          reservedName: "reservedName",
          parse: "parse"
        })
      );
    });
  });

  describe("identifierName", () => {
    function nameForm(name: string, reserved?: readonly string[]) {
      return TestBed.runInInjectionContext(() =>
        form(signal({ name }), (f) => identifierName(f.name, reserved ? { reserved } : undefined))
      );
    }

    it("requires a value", () => {
      expect(kinds(nameForm("").name())).toEqual([ERR.required]);
    });

    it("rejects characters outside the identifier set", () => {
      expect(kinds(nameForm("a b").name())).toEqual([ERR.pattern]);
    });

    it("accepts a valid name without reserved names", () => {
      const f = nameForm("test");
      expect(f().valid()).toBe(true);
    });

    it.each(["test", ".", ".."])("rejects the reserved resolver name %p", (name) => {
      const f = nameForm(name, RESOLVER_RESERVED_NAMES);
      expect(kinds(f.name())).toEqual([ERR.reservedName]);
      expect(f().valid()).toBe(false);
    });

    it("accepts a name that is not reserved", () => {
      expect(nameForm("my-resolver", RESOLVER_RESERVED_NAMES)().valid()).toBe(true);
    });

    it("applies a per-form reserved list", () => {
      expect(kinds(nameForm("test_request", ["test_request"]).name())).toEqual([ERR.reservedName]);
      expect(nameForm("test", ["test_request"])().valid()).toBe(true);
    });
  });

  describe("requiredNonBlank", () => {
    function textForm(text: string) {
      return TestBed.runInInjectionContext(() => form(signal({ text }), (f) => requiredNonBlank(f.text)));
    }

    it("reports one required error for an empty value", () => {
      expect(kinds(textForm("").text())).toEqual([ERR.required]);
    });

    it("rejects whitespace only", () => {
      expect(kinds(textForm("  \t").text())).toEqual([ERR.required]);
    });

    it("accepts text with surrounding whitespace", () => {
      expect(textForm(" a ")().valid()).toBe(true);
    });
  });

  describe("requiredNonEmptyArray", () => {
    function listForm(items: string[]) {
      return TestBed.runInInjectionContext(() => form(signal({ items }), (f) => requiredNonEmptyArray(f.items)));
    }

    it("rejects an empty array", () => {
      expect(kinds(listForm([]).items())).toEqual([ERR.required]);
    });

    it("accepts a non-empty array", () => {
      expect(listForm(["a"])().valid()).toBe(true);
    });
  });

  describe("mustEqual", () => {
    function pinForm(pin: string, repeat: string, kind?: string) {
      const model = signal({ pin, repeat });
      const tree = TestBed.runInInjectionContext(() =>
        form(model, (f) => mustEqual(f.repeat, () => model().pin, kind))
      );
      return { model, tree };
    }

    it("reports pinMismatch by default", () => {
      expect(kinds(pinForm("1234", "12").tree.repeat())).toEqual([ERR.pinMismatch]);
    });

    it("accepts equal values, including two empty ones", () => {
      expect(pinForm("1234", "1234").tree().valid()).toBe(true);
      expect(pinForm("", "").tree().valid()).toBe(true);
    });

    it("re-validates when the other value changes", () => {
      const { model, tree } = pinForm("1234", "1234");
      model.update((m) => ({ ...m, pin: "9" }));
      expect(kinds(tree.repeat())).toEqual([ERR.pinMismatch]);
    });

    it("uses a custom kind", () => {
      expect(kinds(pinForm("a", "b", "custom").tree.repeat())).toEqual(["custom"]);
    });
  });
});
