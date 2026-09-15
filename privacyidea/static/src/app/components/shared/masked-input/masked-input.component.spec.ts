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
import { form, required } from "@angular/forms/signals";
import { By } from "@angular/platform-browser";

import { MaskedInputComponent } from "./masked-input.component";

@Component({
  standalone: true,
  imports: [MaskedInputComponent],
  template: `
    <app-masked-input
      [error]="error()"
      [field]="pinForm"
      [hint]="hint()"
      [label]="label()"
      [placeholder]="placeholder()" />
  `
})
class HostComponent {
  pin = signal("");
  pinForm = form(this.pin, (f) => required(f));
  label = signal("PIN");
  placeholder = signal("");
  hint = signal("");
  error = signal("");
}

describe("MaskedInputComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;
  let component: MaskedInputComponent;

  const input = () => fixture.debugElement.query(By.css("input")).nativeElement as HTMLInputElement;
  const toggleButton = () => fixture.debugElement.query(By.css("button")).nativeElement as HTMLButtonElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    component = fixture.debugElement.query(By.directive(MaskedInputComponent)).componentInstance;
    fixture.detectChanges();
  });

  it("should create the component", () => {
    expect(component).toBeTruthy();
  });

  it("should be masked initially and use a text input", () => {
    expect(component.masked()).toBe(true);
    expect(input().type).toBe("text");
    expect(input().classList).toContain("masked-input");
  });

  it("should disable autocomplete so the browser does not offer to save the value", () => {
    expect(input().getAttribute("autocomplete")).toBe("off");
  });

  it("should render the label and default the optional inputs to empty strings", () => {
    expect(component.label()).toBe("PIN");
    expect(component.placeholder()).toBe("");
    expect(component.hint()).toBe("");
    expect(component.error()).toBe("");
    expect(fixture.nativeElement.querySelector("mat-label").textContent).toContain("PIN");
  });

  it("should toggle masked state when toggleMasked is called", () => {
    component.toggleMasked();
    expect(component.masked()).toBe(false);
    component.toggleMasked();
    expect(component.masked()).toBe(true);
  });

  it("should unmask the input when the suffix button is clicked", () => {
    toggleButton().click();
    fixture.detectChanges();

    expect(component.masked()).toBe(false);
    expect(input().classList).not.toContain("masked-input");
  });

  it("should expose the toggle state via aria-pressed and label it", () => {
    expect(toggleButton().getAttribute("aria-pressed")).toBe("false");
    expect(toggleButton().getAttribute("aria-label")).toBe("PIN");

    toggleButton().click();
    fixture.detectChanges();

    expect(toggleButton().getAttribute("aria-pressed")).toBe("true");
  });

  it("should use a non-submitting button for the toggle", () => {
    expect(toggleButton().type).toBe("button");
  });

  it("should show the visibility icon matching the masked state", () => {
    const icon = () => fixture.nativeElement.querySelector("mat-icon").textContent.trim();
    expect(icon()).toBe("visibility_off");

    component.toggleMasked();
    fixture.detectChanges();

    expect(icon()).toBe("visibility");
  });

  it("should render the placeholder when one is given", () => {
    host.placeholder.set("Enter PIN");
    fixture.detectChanges();

    expect(input().placeholder).toBe("Enter PIN");
  });

  it("should render a hint only when hint is non-empty", () => {
    expect(fixture.nativeElement.querySelector("mat-hint")).toBeNull();

    host.hint.set("At least 4 characters");
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("mat-hint").textContent).toContain("At least 4 characters");
  });

  it("should render an error only when error is non-empty and the field is in an error state", () => {
    expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();

    host.error.set("PINs do not match.");
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();

    host.pinForm().markAsTouched();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("mat-error").textContent).toContain("PINs do not match.");
  });

  it("should write user input back to the bound field", () => {
    input().value = "1234";
    input().dispatchEvent(new Event("input"));
    fixture.detectChanges();

    expect(host.pin()).toBe("1234");
  });
});
