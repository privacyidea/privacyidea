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
import { ChangeDetectionStrategy, Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { hasError } from "./form-state.utils";
import { requiredNonEmptyArray } from "./form-rules.utils";

/**
 * Pins how `[formField]` behaves on `mat-select`, single and multiple.
 */
@Component({
  selector: "app-spike-select",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormField, MatFormFieldModule, MatSelectModule],
  template: `
    <mat-form-field id="single">
      <mat-select [formField]="f.single">
        @for (option of options(); track option) {
          <mat-option [value]="option">{{ option }}</mat-option>
        }
      </mat-select>
      @if (hasError(f.single, "required")) {
        <mat-error>single required</mat-error>
      }
    </mat-form-field>
    <mat-form-field id="multi-required">
      <mat-select
        multiple
        [formField]="f.multiRequired">
        <mat-option value="a">a</mat-option>
        <mat-option value="b">b</mat-option>
      </mat-select>
    </mat-form-field>
    <mat-form-field id="multi-non-empty">
      <mat-select
        multiple
        [formField]="f.multiNonEmpty">
        <mat-option value="a">a</mat-option>
        <mat-option value="b">b</mat-option>
      </mat-select>
      @if (hasError(f.multiNonEmpty, "required")) {
        <mat-error>multi required</mat-error>
      }
    </mat-form-field>
    <mat-form-field id="locked">
      <mat-select [formField]="f.locked">
        @for (option of options(); track option) {
          <mat-option [value]="option">{{ option }}</mat-option>
        }
      </mat-select>
    </mat-form-field>
  `
})
class SpikeSelectComponent {
  readonly hasError = hasError;
  readonly options = signal<string[]>(["a", "b", "c"]);
  readonly model = signal({
    single: "",
    multiRequired: [] as string[],
    multiNonEmpty: [] as string[],
    locked: "b",
    lock: false
  });
  readonly f = form(this.model, (p) => {
    required(p.single);
    required(p.multiRequired);
    requiredNonEmptyArray(p.multiNonEmpty);
    disabled(p.locked, () => this.model().lock);
  });
}

describe("signal forms on mat-select", () => {
  let fixture: ComponentFixture<SpikeSelectComponent>;
  let host: SpikeSelectComponent;
  let el: HTMLElement;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const select = (id: string) => fixture.debugElement.query(By.css(`#${id} mat-select`)).componentInstance as MatSelect;
  const pick = async (id: string, index: number) => {
    select(id).open();
    await flush();
    (document.querySelectorAll("mat-option")[index] as HTMLElement).click();
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SpikeSelectComponent] }).compileComponents();
    fixture = TestBed.createComponent(SpikeSelectComponent);
    host = fixture.componentInstance;
    el = fixture.nativeElement;
    await flush();
  });

  afterEach(() => {
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
  });

  describe("single", () => {
    it("writes a model change to the control", async () => {
      host.model.update((m) => ({ ...m, single: "b" }));
      await flush();
      expect(select("single").value).toBe("b");
    });

    it("writes the picked option to the model and marks the field dirty", async () => {
      expect(host.f.single().dirty()).toBe(false);
      await pick("single", 2);
      expect(host.model().single).toBe("c");
      expect(host.f.single().dirty()).toBe(true);
    });

    it("renders mat-error only after the field is touched", async () => {
      expect(el.querySelector("#single mat-error")).toBeNull();
      host.f.single().markAsTouched();
      await flush();
      expect(el.querySelector("#single mat-error")?.textContent).toContain("single required");
      await pick("single", 0);
      expect(el.querySelector("#single mat-error")).toBeNull();
    });

    it("marks the field touched when the panel closes", async () => {
      expect(host.f.single().touched()).toBe(false);
      select("single").open();
      await flush();
      select("single").close();
      select("single")._onBlur();
      await flush();
      expect(host.f.single().touched()).toBe(true);
    });

    it("pushes disabled() to the control", async () => {
      expect(select("locked").disabled).toBe(false);
      host.model.update((m) => ({ ...m, lock: true }));
      await flush();
      expect(select("locked").disabled).toBe(true);
      expect(host.f.locked().errors()).toEqual([]);
    });

    it("keeps the displayed value of a disabled select whose options arrive later", async () => {
      host.options.set([]);
      host.model.update((m) => ({ ...m, lock: true }));
      await flush();
      host.options.set(["a", "b", "c"]);
      await flush();
      expect(select("locked").value).toBe("b");
      expect(select("locked").triggerValue).toBe("b");
    });
  });

  describe("multiple", () => {
    it("passes the built-in required for an empty array", () => {
      expect(host.model().multiRequired).toEqual([]);
      expect(host.f.multiRequired().errors()).toEqual([]);
      expect(host.f.multiRequired().valid()).toBe(true);
    });

    it("fails requiredNonEmptyArray for an empty array and renders its mat-error when touched", async () => {
      expect(
        host.f
          .multiNonEmpty()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
      host.f.multiNonEmpty().markAsTouched();
      await flush();
      expect(el.querySelector("#multi-non-empty mat-error")?.textContent).toContain("multi required");
    });

    it("writes picked options to the model as an array and marks the field dirty", async () => {
      await pick("multi-non-empty", 0);
      await pick("multi-non-empty", 1);
      expect(host.model().multiNonEmpty).toEqual(["a", "b"]);
      expect(host.f.multiNonEmpty().dirty()).toBe(true);
      expect(host.f.multiNonEmpty().errors()).toEqual([]);
    });

    it("writes a model change to the control", async () => {
      host.model.update((m) => ({ ...m, multiNonEmpty: ["b"] }));
      await flush();
      expect(select("multi-non-empty").value).toEqual(["b"]);
    });
  });
});
