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
import { FieldTree, form, required } from "@angular/forms/signals";
import { blurErrorStateMatcher, clearField, hasError, touchAll } from "./form-state.utils";

describe("form-state.utils", () => {
  interface Model {
    text: string;
    flag: boolean;
    amount: number | null;
    tags: string[];
    params: Record<string, string>;
    nested: { inner: string };
  }

  function createForm(overrides: Partial<Model> = {}) {
    const model = signal<Model>({
      text: "",
      flag: false,
      amount: null,
      tags: [],
      params: { host: "" },
      nested: { inner: "" },
      ...overrides
    });
    const tree = TestBed.runInInjectionContext(() =>
      form(model, (f) => {
        required(f.text);
        required(f.nested.inner);
      })
    );
    return { model, tree };
  }

  describe("hasError", () => {
    it("reports the kind of a string field", () => {
      const { tree } = createForm();
      expect(hasError(tree.text, "required")).toBe(true);
      expect(hasError(tree.text, "pattern")).toBe(false);
    });

    it("clears the error once the value is valid", () => {
      const { model, tree } = createForm();
      model.update((m) => ({ ...m, text: "x" }));
      expect(hasError(tree.text, "required")).toBe(false);
    });

    it("accepts boolean, number | null, string[], Record key and nested fields", () => {
      const { tree } = createForm();
      const key = "host";
      expect(hasError(tree.flag, "required")).toBe(false);
      expect(hasError(tree.amount, "required")).toBe(false);
      expect(hasError(tree.tags, "required")).toBe(false);
      expect(hasError(tree.params[key], "required")).toBe(false);
      expect(hasError(tree.nested.inner, "required")).toBe(true);
    });

    it("accepts the form root", () => {
      const { tree } = createForm();
      expect(hasError(tree, "required")).toBe(false);
    });
  });

  describe("clearField", () => {
    it("sets each field type to its empty value and marks it dirty", () => {
      const { model, tree } = createForm({
        text: "a",
        flag: true,
        amount: 5,
        tags: ["x"],
        params: { host: "h" }
      });
      const key = "host";

      clearField(tree.text, "");
      clearField(tree.flag, false);
      clearField(tree.amount, null);
      clearField(tree.tags, []);
      clearField(tree.params[key], "");

      expect(model()).toEqual(
        expect.objectContaining({ text: "", flag: false, amount: null, tags: [], params: { host: "" } })
      );
      for (const field of [tree.text, tree.flag, tree.amount, tree.tags, tree.params[key]] as FieldTree<unknown>[]) {
        expect(field().dirty()).toBe(true);
      }
    });

    it("leaves a field dirty-free when the value is written through the model", () => {
      const { model, tree } = createForm({ text: "a" });
      model.update((m) => ({ ...m, text: "" }));
      expect(tree.text().dirty()).toBe(false);
    });
  });

  describe("touchAll", () => {
    it("touches every descendant while a root markAsTouched does not", async () => {
      const { tree } = createForm();
      tree().markAsTouched();
      expect(tree().touched()).toBe(true);
      expect(tree.text().touched()).toBe(false);

      await touchAll(tree);

      expect(tree.text().touched()).toBe(true);
      expect(tree.flag().touched()).toBe(true);
      expect(tree.nested.inner().touched()).toBe(true);
      expect(tree.params["host"]().touched()).toBe(true);
    });

    it("touches synchronously and resolves false for an invalid form", async () => {
      const { tree } = createForm();
      const result = touchAll(tree);
      expect(tree.text().touched()).toBe(true);
      expect(await result).toBe(false);
    });

    it("resolves true for a valid form", async () => {
      const { tree } = createForm({ text: "a", nested: { inner: "b" } });
      expect(await touchAll(tree)).toBe(true);
    });

    it("resolves false for a call made while a previous call on the same form is running", async () => {
      const { tree } = createForm({ text: "a", nested: { inner: "b" } });
      const first = touchAll(tree);
      const second = touchAll(tree);
      expect(await second).toBe(false);
      expect(await first).toBe(true);
    });

    it("touches a subtree only", async () => {
      const { tree } = createForm();
      await touchAll(tree.nested);
      expect(tree.nested.inner().touched()).toBe(true);
      expect(tree.text().touched()).toBe(false);
    });
  });

  describe("blurErrorStateMatcher", () => {
    const control = (invalid: boolean, touched: boolean) => ({ invalid, touched }) as never;

    it("shows the error of a touched, invalid control once the field is not focused", () => {
      const matcher = blurErrorStateMatcher(() => false);
      expect(matcher.isErrorState(control(true, true), null)).toBe(true);
    });

    it("hides the error while the field has the focus", () => {
      const focused = signal(true);
      const matcher = blurErrorStateMatcher(focused);
      expect(matcher.isErrorState(control(true, true), null)).toBe(false);
      focused.set(false);
      expect(matcher.isErrorState(control(true, true), null)).toBe(true);
    });

    it("hides the error of a valid or untouched control", () => {
      const matcher = blurErrorStateMatcher(() => false);
      expect(matcher.isErrorState(control(false, true), null)).toBe(false);
      expect(matcher.isErrorState(control(true, false), null)).toBe(false);
      expect(matcher.isErrorState(null, null)).toBe(false);
    });
  });
});
