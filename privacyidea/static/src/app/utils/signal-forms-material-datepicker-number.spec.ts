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
import { disabled, form, FormField, max, min, required } from "@angular/forms/signals";
import { provideNativeDateAdapter } from "@angular/material/core";
import { MatDatepickerModule } from "@angular/material/datepicker";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { hasError } from "./form-state.utils";

/**
 * Pins how `[formField]` behaves on `matDatepicker` inputs and on `type="number"` inputs, including empty values
 * and text the browser cannot parse as a number.
 */
@Component({
  selector: "app-spike-datepicker-number",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormField, MatFormFieldModule, MatInputModule, MatDatepickerModule],
  template: `
    <mat-form-field id="date">
      <input
        matInput
        [matDatepicker]="picker"
        [formField]="f.date" />
      <mat-datepicker #picker />
      @if (hasError(f.date, "required")) {
        <mat-error>date required</mat-error>
      }
    </mat-form-field>
    <mat-form-field id="amount">
      <input
        matInput
        type="number"
        [formField]="f.amount" />
      @if (hasError(f.amount, "required")) {
        <mat-error>amount required</mat-error>
      }
      @if (hasError(f.amount, "parse")) {
        <mat-error>amount not a number</mat-error>
      }
      @if (hasError(f.amount, "min")) {
        <mat-error>amount too small</mat-error>
      }
    </mat-form-field>
    <mat-form-field id="amount-text">
      <input
        matInput
        type="number"
        [formField]="f.amountText" />
    </mat-form-field>
    <mat-form-field id="amount-optional">
      <input
        matInput
        type="number"
        [formField]="f.amountOptional" />
    </mat-form-field>
  `
})
class SpikeDatepickerNumberComponent {
  readonly hasError = hasError;
  readonly model = signal({
    date: null as Date | null,
    amount: null as number | null,
    amountText: "",
    amountOptional: null as number | null,
    lock: false
  });
  readonly f = form(this.model, (p) => {
    required(p.date);
    required(p.amount);
    min(p.amount, 1);
    max(p.amount, 10);
    min(p.amountOptional, 1);
    disabled(p.date, () => this.model().lock);
    disabled(p.amount, () => this.model().lock);
  });
}

describe("signal forms on matDatepicker and number inputs", () => {
  let fixture: ComponentFixture<SpikeDatepickerNumberComponent>;
  let host: SpikeDatepickerNumberComponent;
  let el: HTMLElement;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const input = (id: string) => el.querySelector(`#${id} input`) as HTMLInputElement;
  const type = async (id: string, value: string) => {
    input(id).value = value;
    input(id).dispatchEvent(new Event("input"));
    await flush();
  };
  const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((e) => e.kind);

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SpikeDatepickerNumberComponent],
      providers: [provideNativeDateAdapter()]
    }).compileComponents();
    fixture = TestBed.createComponent(SpikeDatepickerNumberComponent);
    host = fixture.componentInstance;
    el = fixture.nativeElement;
    await flush();
  });

  describe("matDatepicker", () => {
    it("writes a model date to the input", async () => {
      host.model.update((m) => ({ ...m, date: new Date(2026, 0, 5) }));
      await flush();
      expect(input("date").value).toContain("2026");
    });

    it("writes a typed date to the model and marks the field dirty", async () => {
      expect(host.f.date().dirty()).toBe(false);
      await type("date", "1/9/2026");
      expect(host.model().date).toEqual(new Date(2026, 0, 9));
      expect(host.f.date().dirty()).toBe(true);
    });

    it("writes null to the model for text that is not a date", async () => {
      host.model.update((m) => ({ ...m, date: new Date(2026, 0, 5) }));
      await flush();
      await type("date", "garbage");
      expect(host.model().date).toBeNull();
      expect(kinds(host.f.date())).toEqual(["required"]);
    });

    it("marks the field touched on blur and then shows the mat-error", async () => {
      expect(el.querySelector("#date mat-error")).toBeNull();
      input("date").dispatchEvent(new Event("blur"));
      await flush();
      expect(host.f.date().touched()).toBe(true);
      expect(el.querySelector("#date mat-error")?.textContent).toContain("date required");
    });

    it("pushes disabled() to the input", async () => {
      host.model.update((m) => ({ ...m, lock: true }));
      await flush();
      expect(input("date").disabled).toBe(true);
    });
  });

  describe("type=number with a number | null model", () => {
    it("writes a typed number to the model and marks the field dirty", async () => {
      expect(host.f.amount().dirty()).toBe(false);
      await type("amount", "5");
      expect(host.model().amount).toBe(5);
      expect(host.f.amount().dirty()).toBe(true);
      expect(host.f.amount().errors()).toEqual([]);
    });

    it("writes an empty input as null, not 0 or NaN", async () => {
      await type("amount", "5");
      await type("amount", "");
      expect(host.model().amount).toBeNull();
      expect(kinds(host.f.amount())).toEqual(["required"]);
    });

    it("keeps the model and reports a parse error for text the browser cannot parse", async () => {
      await type("amount", "5");
      Object.defineProperty(input("amount"), "validity", { configurable: true, get: () => ({ badInput: true }) });
      await type("amount", "");
      expect(host.model().amount).toBe(5);
      expect(kinds(host.f.amount())).toEqual(["parse"]);
      expect(host.f.amount().valid()).toBe(false);
      expect(host.f().valid()).toBe(false);
    });

    it("reports parse next to required while the model is still empty", async () => {
      Object.defineProperty(input("amount"), "validity", { configurable: true, get: () => ({ badInput: true }) });
      await type("amount", "");
      expect(host.model().amount).toBeNull();
      expect(kinds(host.f.amount())).toEqual(["parse", "required"]);
    });

    it("renders the parse message once the field is touched", async () => {
      Object.defineProperty(input("amount"), "validity", { configurable: true, get: () => ({ badInput: true }) });
      await type("amount", "");
      expect(el.querySelector("#amount mat-error")).toBeNull();
      host.f.amount().markAsTouched();
      await flush();
      const messages = Array.from(el.querySelectorAll("#amount mat-error")).map((e) => e.textContent);
      expect(messages).toContain("amount not a number");
    });

    it("clears the parse error once the input holds a number again", async () => {
      const validity = jest
        .spyOn(input("amount"), "validity", "get")
        .mockReturnValue({ badInput: true } as ValidityState);
      await type("amount", "");
      expect(kinds(host.f.amount())).toEqual(["parse", "required"]);
      validity.mockReturnValue({ badInput: false } as ValidityState);
      await type("amount", "3");
      expect(host.model().amount).toBe(3);
      expect(host.f.amount().errors()).toEqual([]);
    });

    it("applies min and max to a typed number", async () => {
      await type("amount", "0");
      expect(kinds(host.f.amount())).toEqual(["min"]);
      await type("amount", "11");
      expect(kinds(host.f.amount())).toEqual(["max"]);
      await type("amount", "10");
      expect(host.f.amount().errors()).toEqual([]);
    });

    it("skips min on an empty optional number", async () => {
      await type("amount-optional", "5");
      await type("amount-optional", "");
      expect(host.model().amountOptional).toBeNull();
      expect(host.f.amountOptional().errors()).toEqual([]);
    });

    it("pushes disabled() to the input and counts a disabled field as valid", async () => {
      host.model.update((m) => ({ ...m, lock: true }));
      await flush();
      expect(input("amount").disabled).toBe(true);
      expect(host.f.amount().errors()).toEqual([]);
      expect(host.f.amount().invalid()).toBe(false);
    });
  });

  describe("type=number with a string model", () => {
    it("writes the typed text as a string and an empty input as an empty string", async () => {
      await type("amount-text", "42");
      expect(host.model().amountText).toBe("42");
      await type("amount-text", "");
      expect(host.model().amountText).toBe("");
    });

    it("writes a model string to the input", async () => {
      host.model.update((m) => ({ ...m, amountText: "7" }));
      await flush();
      expect(input("amount-text").value).toBe("7");
    });
  });
});
