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
import { MatCheckbox, MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSlideToggle, MatSlideToggleModule } from "@angular/material/slide-toggle";
import { hasError } from "./form-state.utils";

/**
 * Pins how `[formField]` behaves on `mat-checkbox` and `mat-slide-toggle`. Both are bound directly, with no wrapper.
 */
@Component({
  selector: "app-spike-checkbox-toggle",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormField, MatFormFieldModule, MatCheckboxModule, MatSlideToggleModule],
  template: `
    <mat-checkbox
      id="plain"
      [formField]="f.plain"
      >plain</mat-checkbox
    >
    <mat-checkbox
      id="must"
      [formField]="f.must"
      >must</mat-checkbox
    >
    @if (hasError(f.must, "required") && f.must().touched()) {
      <span id="must-error">must be checked</span>
    }
    <mat-checkbox
      id="lockable"
      [formField]="f.lockable"
      >lockable</mat-checkbox
    >
    <mat-slide-toggle
      id="toggle"
      [formField]="f.toggle"
      >toggle</mat-slide-toggle
    >
    <mat-slide-toggle
      id="toggle-lockable"
      [formField]="f.toggleLockable"
      >toggle lockable</mat-slide-toggle
    >
  `
})
class SpikeCheckboxToggleComponent {
  readonly hasError = hasError;
  readonly model = signal({
    plain: false,
    must: false,
    lockable: true,
    toggle: false,
    toggleLockable: true,
    lock: false
  });
  readonly f = form(this.model, (p) => {
    required(p.must);
    required(p.lockable);
    disabled(p.lockable, () => this.model().lock);
    disabled(p.toggleLockable, () => this.model().lock);
  });
}

describe("signal forms on mat-checkbox and mat-slide-toggle", () => {
  let fixture: ComponentFixture<SpikeCheckboxToggleComponent>;
  let host: SpikeCheckboxToggleComponent;
  let el: HTMLElement;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const checkboxInput = (id: string) => el.querySelector(`#${id} input`) as HTMLInputElement;
  const toggleButton = (id: string) => el.querySelector(`#${id} button`) as HTMLButtonElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SpikeCheckboxToggleComponent] }).compileComponents();
    fixture = TestBed.createComponent(SpikeCheckboxToggleComponent);
    host = fixture.componentInstance;
    el = fixture.nativeElement;
    await flush();
  });

  describe("mat-checkbox", () => {
    it("writes a model change to the control", async () => {
      host.model.update((m) => ({ ...m, plain: true }));
      await flush();
      expect(checkboxInput("plain").checked).toBe(true);
      expect(fixture.debugElement.query(By.directive(MatCheckbox)).componentInstance.checked).toBe(true);
    });

    it("writes a click to the model and marks the field dirty", async () => {
      expect(host.f.plain().dirty()).toBe(false);
      checkboxInput("plain").click();
      await flush();
      expect(host.model().plain).toBe(true);
      expect(host.f.plain().dirty()).toBe(true);
    });

    it("marks the field touched on blur", async () => {
      expect(host.f.plain().touched()).toBe(false);
      checkboxInput("plain").dispatchEvent(new Event("blur"));
      await flush();
      expect(host.f.plain().touched()).toBe(true);
    });

    it("treats required as must-be-true", async () => {
      expect(
        host.f
          .must()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
      checkboxInput("must").click();
      await flush();
      expect(host.model().must).toBe(true);
      expect(host.f.must().errors()).toEqual([]);
      checkboxInput("must").click();
      await flush();
      expect(
        host.f
          .must()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
    });

    it("lets the template show an error once the field is touched", async () => {
      expect(el.querySelector("#must-error")).toBeNull();
      host.f.must().markAsTouched();
      await flush();
      expect(el.querySelector("#must-error")).not.toBeNull();
    });

    it("pushes disabled() to the control and counts a disabled field as valid", async () => {
      expect(checkboxInput("lockable").disabled).toBe(false);
      host.model.update((m) => ({ ...m, lock: true, lockable: false }));
      await flush();
      expect(checkboxInput("lockable").disabled).toBe(true);
      expect(fixture.debugElement.query(By.css("#lockable")).componentInstance.disabled).toBe(true);
      expect(host.f.lockable().disabled()).toBe(true);
      expect(host.f.lockable().errors()).toEqual([]);
      expect(host.f.lockable().invalid()).toBe(false);
      expect(host.f().valid()).toBe(false);
    });
  });

  describe("mat-slide-toggle", () => {
    it("writes a model change to the control", async () => {
      host.model.update((m) => ({ ...m, toggle: true }));
      await flush();
      expect(toggleButton("toggle").getAttribute("aria-checked")).toBe("true");
      expect(fixture.debugElement.query(By.directive(MatSlideToggle)).componentInstance.checked).toBe(true);
    });

    it("writes a click to the model and marks the field dirty", async () => {
      expect(host.f.toggle().dirty()).toBe(false);
      toggleButton("toggle").click();
      await flush();
      expect(host.model().toggle).toBe(true);
      expect(host.f.toggle().dirty()).toBe(true);
      toggleButton("toggle").click();
      await flush();
      expect(host.model().toggle).toBe(false);
    });

    it("marks the field touched on blur", async () => {
      toggleButton("toggle").dispatchEvent(new Event("blur"));
      await flush();
      expect(host.f.toggle().touched()).toBe(true);
    });

    it("pushes disabled() to the control", async () => {
      expect(toggleButton("toggle-lockable").disabled).toBe(false);
      host.model.update((m) => ({ ...m, lock: true }));
      await flush();
      expect(toggleButton("toggle-lockable").disabled).toBe(true);
      expect(host.f.toggleLockable().errors()).toEqual([]);
    });
  });

  describe("programmatic writes", () => {
    it("model.update neither marks dirty nor touched", async () => {
      host.model.update((m) => ({ ...m, plain: true, toggle: true }));
      await flush();
      expect(host.f.plain().dirty()).toBe(false);
      expect(host.f.plain().touched()).toBe(false);
      expect(host.f.toggle().dirty()).toBe(false);
    });
  });
});
