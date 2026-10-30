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
import { ChangeDetectionStrategy, Component, linkedSignal, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import {
  applyEach,
  disabled,
  form,
  FormField,
  max,
  maxLength,
  min,
  minLength,
  pattern,
  required
} from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { hasError, touchAll } from "./form-state.utils";

const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((e) => e.kind);

describe("signal forms structure", () => {
  describe("rules that skip empty values", () => {
    function createForm(overrides: { text?: string; amount?: number | null } = {}) {
      const model = signal({ text: "", amount: null as number | null, ...overrides });
      return TestBed.runInInjectionContext(() =>
        form(model, (p) => {
          pattern(p.text, /^[a-z]+$/);
          minLength(p.text, 3);
          maxLength(p.text, 5);
          min(p.amount, 1);
          max(p.amount, 10);
        })
      );
    }

    it("passes pattern, minLength, maxLength, min and max for empty values", () => {
      const f = createForm();
      expect(f.text().errors()).toEqual([]);
      expect(f.amount().errors()).toEqual([]);
      expect(f().valid()).toBe(true);
    });

    it("applies the rules to non-empty values", () => {
      expect(kinds(createForm({ text: "A" }).text())).toEqual(["pattern", "minLength"]);
      expect(kinds(createForm({ text: "abcdefg" }).text())).toEqual(["maxLength"]);
      expect(kinds(createForm({ amount: 0 }).amount())).toEqual(["min"]);
      expect(kinds(createForm({ amount: 11 }).amount())).toEqual(["max"]);
    });

    it("needs a paired required to reject an empty value", () => {
      const model = signal({ text: "" });
      const f = TestBed.runInInjectionContext(() =>
        form(model, (p) => {
          required(p.text);
          pattern(p.text, /^[a-z]+$/);
        })
      );
      expect(kinds(f.text())).toEqual(["required"]);
    });

    it("lets the built-in required accept whitespace and an empty array", () => {
      const model = signal({ text: "   ", list: [] as string[] });
      const f = TestBed.runInInjectionContext(() =>
        form(model, (p) => {
          required(p.text);
          required(p.list);
        })
      );
      expect(f().valid()).toBe(true);
    });
  });

  describe("disabled fields", () => {
    function createForm() {
      const model = signal({ text: "", other: "x", lock: false });
      const tree = TestBed.runInInjectionContext(() =>
        form(model, (p) => {
          required(p.text);
          disabled(p.text, () => model().lock);
        })
      );
      return { model, tree };
    }

    it("counts a disabled required field as valid", () => {
      const { model, tree } = createForm();
      expect(tree().valid()).toBe(false);
      model.update((m) => ({ ...m, lock: true }));
      expect(tree.text().disabled()).toBe(true);
      expect(tree.text().errors()).toEqual([]);
      expect(tree.text().invalid()).toBe(false);
      expect(tree().valid()).toBe(true);
    });

    it("reads touched and dirty as false while disabled", () => {
      const { model, tree } = createForm();
      tree.text().controlValue.set("typed");
      tree.text().markAsTouched();
      expect(tree.text().dirty()).toBe(true);
      expect(tree.text().touched()).toBe(true);
      model.update((m) => ({ ...m, lock: true }));
      expect(tree.text().dirty()).toBe(false);
      expect(tree.text().touched()).toBe(false);
    });

    it("skips a disabled field in touchAll", async () => {
      const { model, tree } = createForm();
      model.update((m) => ({ ...m, lock: true }));
      await touchAll(tree);
      expect(tree.other().touched()).toBe(true);
      expect(tree.text().touched()).toBe(false);
    });
  });

  describe("dirty and touched", () => {
    function createForm() {
      const model = signal({ text: "start", nested: { inner: "a" } });
      const tree = TestBed.runInInjectionContext(() => form(model));
      return { model, tree };
    }

    it("leaves dirty and touched false after model.set and model.update", () => {
      const { model, tree } = createForm();
      model.set({ text: "set", nested: { inner: "b" } });
      model.update((m) => ({ ...m, text: "updated" }));
      expect(tree().dirty()).toBe(false);
      expect(tree.text().dirty()).toBe(false);
      expect(tree.text().touched()).toBe(false);
      expect(tree.text().value()).toBe("updated");
    });

    it("sets dirty through controlValue and markAsDirty and bubbles it to the root", () => {
      const { tree } = createForm();
      tree.nested.inner().controlValue.set("typed");
      expect(tree.nested.inner().dirty()).toBe(true);
      expect(tree().dirty()).toBe(true);
      expect(tree.text().dirty()).toBe(false);
      tree.text().markAsDirty();
      expect(tree.text().dirty()).toBe(true);
    });

    it("clears dirty and touched on reset() and keeps the model value", () => {
      const { model, tree } = createForm();
      tree.text().controlValue.set("typed");
      tree.text().markAsTouched();
      tree().reset();
      expect(tree().dirty()).toBe(false);
      expect(tree.text().dirty()).toBe(false);
      expect(tree.text().touched()).toBe(false);
      expect(model().text).toBe("typed");
    });

    it("replaces the model on reset(value)", () => {
      const { model, tree } = createForm();
      tree.text().controlValue.set("typed");
      tree().reset({ text: "fresh", nested: { inner: "z" } });
      expect(model()).toEqual({ text: "fresh", nested: { inner: "z" } });
      expect(tree().dirty()).toBe(false);
    });

    it("touches a field again after reset()", () => {
      const { tree } = createForm();
      tree.text().markAsTouched();
      tree().reset();
      tree.text().markAsTouched();
      expect(tree.text().touched()).toBe(true);
    });

    it("does not clear dirty when the value is edited back to the start value", () => {
      const { tree } = createForm();
      tree.text().controlValue.set("typed");
      tree.text().controlValue.set("start");
      expect(tree.text().dirty()).toBe(true);
    });
  });

  describe("touch propagation to mat-error", () => {
    @Component({
      selector: "app-spike-touch",
      changeDetection: ChangeDetectionStrategy.OnPush,
      imports: [FormField, MatFormFieldModule, MatInputModule],
      template: `
        <mat-form-field id="first">
          <input
            matInput
            [formField]="f.first" />
          @if (hasError(f.first, "required")) {
            <mat-error>first required</mat-error>
          }
        </mat-form-field>
        <mat-form-field id="second">
          <input
            matInput
            [formField]="f.nested.second" />
          @if (hasError(f.nested.second, "required")) {
            <mat-error>second required</mat-error>
          }
        </mat-form-field>
      `
    })
    class SpikeTouchComponent {
      readonly hasError = hasError;
      readonly model = signal({ first: "", nested: { second: "" } });
      readonly f = form(this.model, (p) => {
        required(p.first);
        required(p.nested.second);
      });
    }

    let fixture: ComponentFixture<SpikeTouchComponent>;
    let host: SpikeTouchComponent;
    const flush = async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const errorCount = () => fixture.nativeElement.querySelectorAll("mat-error").length;

    beforeEach(async () => {
      await TestBed.configureTestingModule({ imports: [SpikeTouchComponent] }).compileComponents();
      fixture = TestBed.createComponent(SpikeTouchComponent);
      host = fixture.componentInstance;
      await flush();
    });

    it("renders no mat-error for untouched invalid fields", () => {
      expect(host.f().valid()).toBe(false);
      expect(errorCount()).toBe(0);
    });

    it("does not reach the children when only the root is marked touched", async () => {
      host.f().markAsTouched();
      await flush();
      expect(host.f().touched()).toBe(true);
      expect(host.f.first().touched()).toBe(false);
      expect(host.f.nested.second().touched()).toBe(false);
      expect(errorCount()).toBe(0);
    });

    it("renders every mat-error after touchAll", async () => {
      await touchAll(host.f);
      await flush();
      expect(host.f.first().touched()).toBe(true);
      expect(host.f.nested.second().touched()).toBe(true);
      expect(errorCount()).toBe(2);
    });
  });

  describe("lists", () => {
    interface Row {
      n: string;
    }

    @Component({
      selector: "app-spike-rows",
      changeDetection: ChangeDetectionStrategy.OnPush,
      imports: [FormField],
      template: `
        @for (row of f.rows; track row) {
          <input
            class="by-field"
            [formField]="row.n" />
        }
      `
    })
    class SpikeRowsComponent {
      readonly model = signal({ rows: [{ n: "a" }, { n: "b" }] as Row[] });
      readonly f = form(this.model, (p) => applyEach(p.rows, (row) => required(row.n)));
    }

    @Component({
      selector: "app-spike-rows-by-value",
      changeDetection: ChangeDetectionStrategy.OnPush,
      imports: [FormField],
      template: `
        @for (row of f.rows; track row().value()) {
          <input
            class="by-value"
            [formField]="row.n" />
        }
      `
    })
    class SpikeRowsByValueComponent {
      readonly model = signal({ rows: [{ n: "a" }, { n: "b" }] as Row[] });
      readonly f = form(this.model, (p) => applyEach(p.rows, (row) => required(row.n)));
    }

    const flush = async (fixture: ComponentFixture<unknown>) => {
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };

    it("tracks rows by FieldTree so typing keeps the input and add and remove work", async () => {
      const fixture = TestBed.createComponent(SpikeRowsComponent);
      const host = fixture.componentInstance;
      await flush(fixture);
      const inputs = () => Array.from(fixture.nativeElement.querySelectorAll(".by-field")) as HTMLInputElement[];
      const first = inputs()[0];

      first.value = "typed";
      first.dispatchEvent(new Event("input"));
      await flush(fixture);
      expect(host.model().rows.map((row) => row.n)).toEqual(["typed", "b"]);
      expect(inputs()[0]).toBe(first);

      host.model.update((m) => ({ rows: [...m.rows, { n: "" }] }));
      await flush(fixture);
      expect(inputs().length).toBe(3);
      expect(kinds(host.f.rows[2].n())).toEqual(["required"]);

      host.model.update((m) => ({ rows: m.rows.filter((_, index) => index !== 0) }));
      await flush(fixture);
      expect(inputs().length).toBe(2);
      expect(host.model().rows.map((row) => row.n)).toEqual(["b", ""]);
    });

    it("adds an own symbol key to the row objects of the model", async () => {
      const fixture = TestBed.createComponent(SpikeRowsComponent);
      await flush(fixture);
      expect(Object.getOwnPropertySymbols(fixture.componentInstance.model().rows[0]).length).toBe(1);
    });

    it("throws NG01904 when a row is tracked by its value and a row is removed", async () => {
      const fixture = TestBed.createComponent(SpikeRowsByValueComponent);
      await flush(fixture);
      fixture.componentInstance.model.update((m) => ({ rows: m.rows.filter((_, index) => index !== 0) }));
      await expect(flush(fixture)).rejects.toThrow(/NG01904/);
    });

    it("throws for frozen row objects", () => {
      const model = signal({ rows: [] as Row[] });
      const f = TestBed.runInInjectionContext(() => form(model));
      model.set({ rows: [Object.freeze({ n: "a" })] });
      expect(() => f.rows[0].n().value()).toThrow(TypeError);
    });
  });

  describe("dynamic-key Record models", () => {
    function createForm(initial: Record<string, string>) {
      const model = signal<Record<string, string>>(initial);
      const tree = TestBed.runInInjectionContext(() => form(model, (p) => applyEach(p, (value) => required(value))));
      return { model, tree };
    }

    it("creates a typed field for every key the model holds", () => {
      const { model, tree } = createForm({ host: "h", port: "" });
      const key = "port";
      expect(tree[key]().value()).toBe("");
      expect(kinds(tree[key]())).toEqual(["required"]);
      expect(kinds(tree["host"]())).toEqual([]);
      expect(model()).toEqual({ host: "h", port: "" });
    });

    it("writes through a dynamic key and marks it dirty", () => {
      const { model, tree } = createForm({ host: "h" });
      const key = "host";
      tree[key]().controlValue.set("other");
      expect(model()).toEqual({ host: "other" });
      expect(tree[key]().dirty()).toBe(true);
    });

    it("creates fields, with the schema applied, for keys added after construction", () => {
      const { model, tree } = createForm({ host: "h" });
      model.update((m) => ({ ...m, later: "" }));
      const key = "later";
      expect(typeof tree[key]).toBe("function");
      expect(kinds(tree[key]())).toEqual(["required"]);
    });

    it("has no field for a key the model does not hold", () => {
      const { tree } = createForm({ host: "h" });
      const key = "missing";
      expect(tree[key] as unknown).toBeUndefined();
      expect(Object.keys(tree)).toEqual(["host"]);
    });

    it("has no field for a key whose value is undefined", () => {
      const { model, tree } = createForm({ host: "h" });
      model.update((m) => ({ ...m, gone: undefined as unknown as string }));
      expect(tree["gone"] as unknown).toBeUndefined();
    });

    it("drops the field of a removed key", () => {
      const { model, tree } = createForm({ host: "h", port: "1" });
      model.set({ host: "h" });
      expect(tree["port"] as unknown).toBeUndefined();
      expect(tree["host"]().value()).toBe("h");
    });

    it("accepts a rule on a single explicit key", () => {
      const model = signal<Record<string, string>>({ host: "" });
      const tree = TestBed.runInInjectionContext(() => form(model, (p) => required(p["host"])));
      expect(kinds(tree["host"]())).toEqual(["required"]);
    });

    describe("in a template", () => {
      @Component({
        selector: "app-spike-record",
        changeDetection: ChangeDetectionStrategy.OnPush,
        imports: [FormField],
        template: `
          @for (key of keys(); track key) {
            <input
              class="entry"
              [attr.data-key]="key"
              [formField]="f[key]" />
          }
        `
      })
      class SpikeRecordComponent {
        readonly model = signal<Record<string, string>>({ host: "h", port: "1" });
        readonly keys = () => Object.keys(this.model());
        readonly f = form(this.model, (p) => applyEach(p, (value) => required(value)));
      }

      it("binds inputs to dynamic keys and renders inputs for added keys", async () => {
        const fixture = TestBed.createComponent(SpikeRecordComponent);
        const host = fixture.componentInstance;
        const flush = async () => {
          fixture.detectChanges();
          await fixture.whenStable();
          fixture.detectChanges();
        };
        await flush();
        const entries = () => Array.from(fixture.nativeElement.querySelectorAll(".entry")) as HTMLInputElement[];
        expect(entries().map((e) => e.value)).toEqual(["h", "1"]);

        entries()[1].value = "2";
        entries()[1].dispatchEvent(new Event("input"));
        await flush();
        expect(host.model()).toEqual({ host: "h", port: "2" });
        expect(host.f["port"]().dirty()).toBe(true);

        host.model.update((m) => ({ ...m, extra: "x" }));
        await flush();
        expect(entries().map((e) => e.dataset["key"])).toEqual(["host", "port", "extra"]);
        expect(entries()[2].value).toBe("x");
      });
    });
  });

  describe("form() over other signals", () => {
    it("re-seeds from a linkedSignal source and keeps dirty until reset()", () => {
      const source = signal("one");
      const model = TestBed.runInInjectionContext(() => linkedSignal(() => ({ value: source() })));
      const tree = TestBed.runInInjectionContext(() => form(model));

      tree.value().controlValue.set("typed");
      expect(model()).toEqual({ value: "typed" });
      expect(tree().dirty()).toBe(true);

      source.set("two");
      expect(model()).toEqual({ value: "two" });
      expect(tree.value().value()).toBe("two");
      expect(tree().dirty()).toBe(true);

      tree().reset();
      expect(tree().dirty()).toBe(false);
      expect(model()).toEqual({ value: "two" });
    });

    it("writes through to a shared string | null signal and follows its changes", () => {
      const shared = signal<string | null>(null);
      const tree = TestBed.runInInjectionContext(() => form(shared, (p) => required(p)));
      expect(kinds(tree())).toEqual(["required"]);

      tree().controlValue.set("serial");
      expect(shared()).toBe("serial");
      expect(tree().errors()).toEqual([]);

      shared.set(null);
      expect(tree().value()).toBeNull();
      expect(kinds(tree())).toEqual(["required"]);
    });

    it("holds a string | UserData union and reads the current member", () => {
      interface UserData {
        username: string;
      }
      const shared = signal<string | UserData | null>("al");
      const tree = TestBed.runInInjectionContext(() => form(shared));
      expect(tree().value()).toBe("al");

      shared.set({ username: "alice" });
      expect(tree().value()).toEqual({ username: "alice" });

      tree().controlValue.set("typed");
      expect(shared()).toBe("typed");
    });
  });
});
