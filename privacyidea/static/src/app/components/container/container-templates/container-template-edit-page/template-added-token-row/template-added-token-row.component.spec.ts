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

import { Component, Input } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { EnrollTokenTypeSwitchComponent } from "@components/shared/enroll-token-type-switch/enroll-token-type-switch.component";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { TemplateAddedTokenRowComponent } from "./template-added-token-row.component";

@Component({
  selector: "app-enroll-token-type-switch",
  standalone: true,
  template: ""
})
class StubEnrollTokenTypeSwitchComponent {
  @Input() tokenTypeKey!: string;
  @Input() enrollmentData: TokenEnrollmentData | null = null;
}

describe("TemplateAddedTokenRowComponent", () => {
  let component: TemplateAddedTokenRowComponent;
  let fixture: ComponentFixture<TemplateAddedTokenRowComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TemplateAddedTokenRowComponent]
    })
      .overrideComponent(TemplateAddedTokenRowComponent, {
        remove: { imports: [EnrollTokenTypeSwitchComponent] },
        add: { imports: [StubEnrollTokenTypeSwitchComponent] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(TemplateAddedTokenRowComponent);
    component = fixture.componentInstance;

    // Set required inputs before any effect/signal runs
    fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp" });
    fixture.componentRef.setInput("index", 0);
  });

  const checkboxes = (): HTMLInputElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-checkbox input[type=checkbox]"));
  const assignCheckbox = (): HTMLInputElement => checkboxes()[0];
  const changePinCheckbox = (): HTMLInputElement => checkboxes()[1];

  describe("Core Functionality", () => {
    it("should create", () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it("should render the token type switch with the payload type", () => {
      fixture.detectChanges();

      const switchElement = fixture.debugElement.query(By.css("app-enroll-token-type-switch"));
      expect(switchElement).toBeTruthy();
      expect(switchElement.componentInstance.tokenTypeKey).toBe("hotp");
    });

    it("should keep the expansion panel enabled regardless of token type", () => {
      fixture.detectChanges();

      const panel = fixture.debugElement.query(By.css("mat-expansion-panel"));
      expect(panel.componentInstance.disabled).toBe(false);
    });

    it("should expose the token type description", () => {
      fixture.detectChanges();

      expect(component.tokenTypeDescription()).toContain("HOTP");
    });

    it("names the delete button", () => {
      fixture.detectChanges();

      const deleteBtn: HTMLButtonElement = fixture.nativeElement.querySelector("button[mat-icon-button]");
      expect(deleteBtn.getAttribute("aria-label")).toBe("Remove Token");
    });

    it("should emit removeToken when delete button is clicked", () => {
      fixture.componentRef.setInput("index", 5);
      const spy = jest.spyOn(component.removeToken, "emit");
      fixture.detectChanges();

      const deleteBtn = fixture.debugElement.query(By.css("button[mat-icon-button]"));
      deleteBtn.nativeElement.click();

      expect(spy).toHaveBeenCalledWith(5);
    });

    it("the assign-to-user checkbox writes the userAssign signal and marks its field dirty", () => {
      fixture.detectChanges();
      expect(component.userAssign()).toBe(false);

      assignCheckbox().click();
      fixture.detectChanges();

      expect(component.userAssign()).toBe(true);
      expect(component.userAssignField().dirty()).toBe(true);
    });

    it("the assign-to-user checkbox shows the user flag of the payload", () => {
      fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp", user: true });
      fixture.detectChanges();

      expect(assignCheckbox().checked).toBe(true);
    });

    it("the assign-to-user checkbox follows a new payload", () => {
      fixture.detectChanges();
      assignCheckbox().click();
      fixture.detectChanges();
      fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp", user: false });
      fixture.detectChanges();

      expect(component.userAssign()).toBe(false);
      expect(assignCheckbox().checked).toBe(false);
    });

    it("clicking the assign-to-user checkbox leaves the expansion panel closed", () => {
      fixture.detectChanges();

      assignCheckbox().click();
      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css("mat-expansion-panel")).componentInstance.expanded).toBe(false);
    });

    it("the change-PIN checkbox is unchecked by default", () => {
      fixture.detectChanges();

      expect(component.changePinOnFirstUse()).toBe(false);
      expect(changePinCheckbox().checked).toBe(false);
    });

    it("the change-PIN checkbox writes the changePinOnFirstUse signal and marks its field dirty", () => {
      fixture.detectChanges();

      changePinCheckbox().click();
      fixture.detectChanges();

      expect(component.changePinOnFirstUse()).toBe(true);
      expect(component.changePinOnFirstUseField().dirty()).toBe(true);
      expect(component.userAssign()).toBe(false);
    });

    it("the change-PIN checkbox shows the flag of the payload", () => {
      fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp", change_pin_on_first_use: true });
      fixture.detectChanges();

      expect(changePinCheckbox().checked).toBe(true);
    });

    it("the change-PIN checkbox follows a new payload", () => {
      fixture.detectChanges();
      changePinCheckbox().click();
      fixture.detectChanges();
      fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp", change_pin_on_first_use: false });
      fixture.detectChanges();

      expect(component.changePinOnFirstUse()).toBe(false);
      expect(changePinCheckbox().checked).toBe(false);
    });

    it("clicking the change-PIN checkbox leaves the expansion panel closed", () => {
      fixture.detectChanges();

      changePinCheckbox().click();
      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css("mat-expansion-panel")).componentInstance.expanded).toBe(false);
    });

    for (const [name, checkbox] of [
      ["assign-to-user", assignCheckbox],
      ["change-PIN", changePinCheckbox]
    ] as const) {
      for (const [key, keyCode] of [
        ["Enter", 13],
        [" ", 32]
      ] as const) {
        it(`pressing "${key}" on the ${name} checkbox leaves the expansion panel closed`, () => {
          fixture.detectChanges();
          const event = new KeyboardEvent("keydown", { key, keyCode, bubbles: true, cancelable: true });

          checkbox().dispatchEvent(event);
          fixture.detectChanges();

          expect(fixture.debugElement.query(By.css("mat-expansion-panel")).componentInstance.expanded).toBe(false);
          expect(event.defaultPrevented).toBe(false);
        });
      }
    }

    it("getCurrentPayload falls back to the input payload (with template flags) when no strategy is available", () => {
      fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp", description: "x" });
      fixture.detectChanges();
      component.userAssign.set(true);

      expect(component.getCurrentPayload()).toEqual({
        type: "hotp",
        description: "x",
        user: true,
        change_pin_on_first_use: false
      });
    });

    it("getCurrentPayload sends the current value of the change-PIN checkbox", () => {
      fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp", change_pin_on_first_use: true });
      fixture.detectChanges();

      expect(component.getCurrentPayload()).toEqual({ type: "hotp", user: false, change_pin_on_first_use: true });

      component.changePinOnFirstUse.set(false);

      expect(component.getCurrentPayload()).toEqual({ type: "hotp", user: false, change_pin_on_first_use: false });
    });

    it("getCurrentPayload returns the strategy's mapped payload when valid", () => {
      fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp", description: "x" });
      fixture.detectChanges();
      component.userAssign.set(true);

      const buildEnrollmentArgs = jest.fn().mockReturnValue({
        data: { type: "hotp", customField: "v" },
        mapper: { toApiPayload: (d: Record<string, unknown>) => ({ ...d, mapped: true }) }
      });
      Object.defineProperty(component, "enrollSwitch", {
        value: () => ({ currentStrategy: () => ({ buildEnrollmentArgs }) }),
        configurable: true
      });

      expect(component.getCurrentPayload()).toEqual({
        type: "hotp",
        customField: "v",
        mapped: true,
        user: true,
        change_pin_on_first_use: false
      });
      expect(buildEnrollmentArgs).toHaveBeenCalledWith(expect.objectContaining({ type: "hotp" }));
    });

    it("getCurrentPayload returns null when the strategy's form is invalid", () => {
      fixture.detectChanges();
      const buildEnrollmentArgs = jest.fn().mockReturnValue(null);
      Object.defineProperty(component, "enrollSwitch", {
        value: () => ({ currentStrategy: () => ({ buildEnrollmentArgs }) }),
        configurable: true
      });

      expect(component.getCurrentPayload()).toBeNull();
    });
  });

  describe("Lifecycle & UI Logic", () => {
    it("should stop propagation on delete button click", () => {
      fixture.detectChanges();

      const deleteBtn = fixture.debugElement.query(By.css("button[mat-icon-button]"));
      const clickEvent = new MouseEvent("click", { bubbles: true, cancelable: true });
      const stopSpy = jest.spyOn(clickEvent, "stopPropagation");

      deleteBtn.nativeElement.dispatchEvent(clickEvent);

      expect(stopSpy).toHaveBeenCalled();
    });

    it("should handle invalid index by not emitting remove event", () => {
      fixture.componentRef.setInput("index", -1);
      const spy = jest.spyOn(component.removeToken, "emit");
      fixture.detectChanges();

      component.emitRemoveToken();
      expect(spy).not.toHaveBeenCalled();
    });

    it("scrollIntoView opens the expansion panel and scrolls", () => {
      fixture.detectChanges();
      const hostElement = fixture.debugElement.nativeElement as HTMLElement;
      const scrollSpy = jest.fn();
      hostElement.scrollIntoView = scrollSpy;

      const panel = fixture.debugElement.query(By.css("mat-expansion-panel")).componentInstance;
      const openSpy = jest.spyOn(panel, "open");

      component.scrollIntoView();

      expect(openSpy).toHaveBeenCalled();
      expect(scrollSpy).toHaveBeenCalledWith({ behavior: "smooth", block: "center" });
    });
  });
});
