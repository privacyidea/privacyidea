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

import { Component, EventEmitter, Output } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { EnrollHotpComponent } from "@components/token/token-enrollment/enroll-hotp/enroll-hotp.component";
import { TemplateAddedTokenRowComponent } from "./template-added-token-row.component";

@Component({
  selector: "app-enroll-hotp",
  standalone: true,
  template: ""
})
class MockEnrollHotpComponent {
  @Output() additionalFormFieldsChange = new EventEmitter<any>();
}

describe("TemplateAddedTokenRowComponent", () => {
  let component: TemplateAddedTokenRowComponent;
  let fixture: ComponentFixture<TemplateAddedTokenRowComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TemplateAddedTokenRowComponent, NoopAnimationsModule]
    })
      .overrideComponent(TemplateAddedTokenRowComponent, {
        remove: { imports: [EnrollHotpComponent] },
        add: { imports: [MockEnrollHotpComponent] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(TemplateAddedTokenRowComponent);
    component = fixture.componentInstance;

    // Set required inputs before any effect/signal runs
    fixture.componentRef.setInput("tokenEnrollmentPayload", { type: "hotp" });
    fixture.componentRef.setInput("index", 0);
  });

  describe("Core Functionality", () => {
    it("should create", () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it("should render the correct child component based on token type", () => {
      fixture.detectChanges();

      const hotpChild = fixture.debugElement.query(By.css("app-enroll-hotp"));
      expect(hotpChild).toBeTruthy();
    });

    it("should disable expansion panel if child has no form fields", () => {
      fixture.detectChanges();

      expect(component.childHadNoForm()).toBe(true);
      const panel = fixture.debugElement.query(By.css("mat-expansion-panel"));
      expect(panel.componentInstance.disabled).toBe(true);
    });

    it("should emit onRemoveToken when delete button is clicked", () => {
      fixture.componentRef.setInput("index", 5);
      const spy = jest.spyOn(component.onRemoveToken, "emit");
      fixture.detectChanges();

      const deleteBtn = fixture.debugElement.query(By.css("button[mat-icon-button]"));
      deleteBtn.nativeElement.click();

      expect(spy).toHaveBeenCalledWith(5);
    });

    it("emits onEditToken when the enrollmentArgsGetter is registered and returns args", () => {
      const spy = jest.spyOn(component.onEditToken, "emit");
      fixture.detectChanges();

      component.updateEnrollmentArgsGetter((data) => ({
        data: { ...data, testKey: "updatedValue" } as any,
        mapper: { toApiPayload: (d: any) => d } as any
      }));

      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          testKey: "updatedValue"
        })
      );
    });
  });

  describe("Lifecycle & UI Logic", () => {
    it("should update childHadNoForm to false when fields are added", () => {
      fixture.detectChanges();

      expect(component.childHadNoForm()).toBe(true);

      component.updateAdditionalFormFields({ pin: {} });
      fixture.detectChanges();

      expect(component.childHadNoForm()).toBe(false);
    });

    it("should set childHadForm back to false when no fields are passed", () => {
      component.updateAdditionalFormFields({ key: {} });
      expect(component.childHadForm()).toBe(true);

      component.updateAdditionalFormFields({});
      expect(component.childHadForm()).toBe(false);
    });

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
      const spy = jest.spyOn(component.onRemoveToken, "emit");
      fixture.detectChanges();

      component.removeToken();
      expect(spy).not.toHaveBeenCalled();
    });
  });
});
