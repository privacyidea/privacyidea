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
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { form, validate } from "@angular/forms/signals";
import { By } from "@angular/platform-browser";

import { MaskedInputComponent } from "../masked-input/masked-input.component";
import { EnrollmentPinComponent } from "./enrollment-pin.component";

@Component({
  standalone: true,
  imports: [EnrollmentPinComponent],
  template: `
    <app-enrollment-pin
      [repeatPinControl]="repeatPinForm"
      [setPinControl]="setPinForm" />
  `
})
class HostComponent {
  pin = signal("");
  repeatPin = signal("");
  setPinForm = form(this.pin);
  repeatPinForm = form(this.repeatPin, (f) =>
    validate(f, (ctx) => (ctx.value() !== this.pin() ? [{ kind: "pinMismatch" }] : []))
  );
}

describe("EnrollmentPinComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;
  let component: EnrollmentPinComponent;

  const maskedInputs = () => fixture.debugElement.queryAll(By.directive(MaskedInputComponent));

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    component = fixture.debugElement.query(By.directive(EnrollmentPinComponent)).componentInstance;
    fixture.detectChanges();
  });

  it("should create the component", () => {
    expect(component).toBeTruthy();
  });

  it("should render a masked input for the PIN and the repeated PIN", () => {
    const inputs = maskedInputs();
    expect(inputs.length).toBe(2);
    expect(inputs[0].componentInstance.label()).toBe("PIN");
    expect(inputs[1].componentInstance.label()).toBe("Repeat PIN");
    expect(inputs[0].componentInstance.masked()).toBe(true);
    expect(inputs[1].componentInstance.masked()).toBe(true);
  });

  it("should have no mismatch error while both fields are untouched", () => {
    host.repeatPin.set("other");
    fixture.detectChanges();

    expect(component.pinMismatchError()).toBe("");
  });

  it("should report a mismatch once the PIN field is touched", () => {
    host.pin.set("1234");
    host.repeatPin.set("5678");
    host.setPinForm().markAsTouched();
    fixture.detectChanges();

    expect(component.pinMismatchError()).toBe("PINs do not match.");
  });

  it("should report a mismatch once the repeat field is touched", () => {
    host.pin.set("1234");
    host.repeatPin.set("5678");
    host.repeatPinForm().markAsTouched();
    fixture.detectChanges();

    expect(component.pinMismatchError()).toBe("PINs do not match.");
  });

  it("should clear the mismatch error when the PINs match", () => {
    host.pin.set("1234");
    host.repeatPin.set("5678");
    host.repeatPinForm().markAsTouched();
    fixture.detectChanges();
    expect(component.pinMismatchError()).toBe("PINs do not match.");

    host.repeatPin.set("1234");
    fixture.detectChanges();

    expect(component.pinMismatchError()).toBe("");
  });

  it("should pass the mismatch error to the repeat input only", () => {
    host.pin.set("1234");
    host.repeatPin.set("5678");
    host.repeatPinForm().markAsTouched();
    fixture.detectChanges();

    const inputs = maskedInputs();
    expect(inputs[0].componentInstance.error()).toBe("");
    expect(inputs[1].componentInstance.error()).toBe("PINs do not match.");
  });

  it("should write both inputs back to the bound fields", () => {
    const inputs = fixture.debugElement.queryAll(By.css("input"));
    const setValue = (element: HTMLInputElement, value: string) => {
      element.value = value;
      element.dispatchEvent(new Event("input"));
    };

    setValue(inputs[0].nativeElement, "1234");
    setValue(inputs[1].nativeElement, "1234");
    fixture.detectChanges();

    expect(host.pin()).toBe("1234");
    expect(host.repeatPin()).toBe("1234");
    expect(component.pinMismatchError()).toBe("");
  });
});
