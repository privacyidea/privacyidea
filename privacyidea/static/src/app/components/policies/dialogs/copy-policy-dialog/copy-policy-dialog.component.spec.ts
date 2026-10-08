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

import { Component, input, output } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { DialogAction } from "@models/dialog";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { CopyPolicyDialogComponent } from "./copy-policy-dialog.component";

class MockMatDialogRef {
  close = jest.fn();
}

@Component({
  selector: "app-dialog-wrapper",
  template: "<ng-content></ng-content>",
  standalone: true
})
class MockDialogWrapperComponent {
  title = input.required<string>();
  actions = input.required<DialogAction<"submit" | null>[]>();
  showCloseButton = input<boolean>(true);
  wrapperClose = output<void>();
  actionTriggered = output<"submit" | null>();
}

describe("CopyPolicyDialogComponent", () => {
  let component: CopyPolicyDialogComponent;
  let fixture: ComponentFixture<CopyPolicyDialogComponent>;
  let dialogRef: MockMatDialogRef;
  let policyService: MockPolicyService;
  const initialPolicyName = "Original_Policy";
  const existingPolicy = (name: string): PolicyDetail => ({ ...policyService.getEmptyPolicy(), name });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CopyPolicyDialogComponent],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: initialPolicyName },
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    })
      .overrideComponent(CopyPolicyDialogComponent, {
        set: {
          imports: [MockDialogWrapperComponent]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(CopyPolicyDialogComponent);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    policyService.allPolicies.set([existingPolicy(initialPolicyName), existingPolicy("Other_Policy")]);
    fixture.detectChanges();
  });

  describe("1. Validator Logic", () => {
    it("should reject unchanged names with 'notChanged' error", () => {
      component.nameSignal.set(initialPolicyName);
      expect(
        component
          .nameField()
          .errors()
          .some((e) => e.kind === "notChanged")
      ).toBe(true);
      expect(component.nameField().valid()).toBe(false);
    });

    it("should be valid when the name is changed", () => {
      component.nameSignal.set("Modified_Policy_Name");
      expect(
        component
          .nameField()
          .errors()
          .some((e) => e.kind === "notChanged")
      ).toBe(false);
      expect(component.nameField().valid()).toBe(true);
    });

    it("should reject empty names (required)", () => {
      component.nameSignal.set("");
      expect(
        component
          .nameField()
          .errors()
          .some((e) => e.kind === "required")
      ).toBe(true);
    });
  });

  describe("1b. Name collision", () => {
    const errorKinds = () =>
      component
        .nameField()
        .errors()
        .map((e) => e.kind);

    it("should reject the name of another existing policy with 'nameTaken' error", () => {
      component.nameSignal.set("Other_Policy");
      expect(errorKinds()).toContain("nameTaken");
      expect(component.nameField().valid()).toBe(false);
      expect(component.isInvalid()).toBe(true);
    });

    it("should report the unchanged original name as 'notChanged' only", () => {
      component.nameSignal.set(initialPolicyName);
      expect(errorKinds()).toEqual(["notChanged"]);
    });

    it("should accept a name that no policy carries", () => {
      component.nameSignal.set("Free_Name");
      expect(errorKinds()).not.toContain("nameTaken");
      expect(component.nameField().valid()).toBe(true);
    });

    it("should ignore the case of the name, which MySQL and MariaDB do as well", () => {
      component.nameSignal.set("other_policy");
      expect(errorKinds()).toContain("nameTaken");
    });

    it("should report a case variant of the original name", () => {
      component.nameSignal.set("ORIGINAL_POLICY");
      expect(errorKinds()).toEqual(["nameTaken"]);
    });

    it("should reject a name that was taken by a copy made in the meantime", () => {
      component.nameSignal.set("Copy_Name");
      expect(component.nameField().valid()).toBe(true);

      policyService.allPolicies.set([...policyService.allPolicies(), existingPolicy("Copy_Name")]);

      expect(errorKinds()).toContain("nameTaken");
    });

    it("should show the error message of the collision at once, without the field having lost focus", () => {
      expect(component.nameField().touched()).toBe(false);

      component.nameSignal.set("Other_Policy");
      fixture.detectChanges();

      expect(component.nameField().touched()).toBe(true);
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain(
        "A policy with this name already exists."
      );
    });

    it("should leave the field untouched while the name is free", () => {
      component.nameSignal.set("Free_Name");
      fixture.detectChanges();

      expect(component.nameField().touched()).toBe(false);
    });
  });

  describe("2. UI Actions State", () => {
    it("should disable confirm/submit action when the form is invalid", () => {
      component.nameSignal.set(initialPolicyName);
      fixture.detectChanges();

      const submitAction = component.actions().find((a) => a.value === "submit");
      expect(submitAction?.disabled).toBe(true);
    });

    it("should enable confirm/submit action when the form is valid", () => {
      component.nameSignal.set("New_Unique_Name");
      fixture.detectChanges();

      const submitAction = component.actions().find((a) => a.value === "submit");
      expect(submitAction?.disabled).toBe(false);
    });
  });

  describe("2b. UI Actions State on collision", () => {
    it("should disable confirm/submit action when the name is taken", () => {
      component.nameSignal.set("Other_Policy");
      fixture.detectChanges();

      const submitAction = component.actions().find((a) => a.value === "submit");
      expect(submitAction?.disabled).toBe(true);
    });
  });

  describe("3. onAction Flow", () => {
    it("should return the new name only when valid on submit", () => {
      const newName = "Valid_New_Name";
      component.nameSignal.set(newName);

      component.onAction("submit");
      expect(dialogRef.close).toHaveBeenCalledWith(newName);
    });

    it("should return null on submit if the form is invalid", () => {
      component.nameSignal.set(initialPolicyName);

      component.onAction("submit");
      expect(dialogRef.close).toHaveBeenCalledWith(null);
    });

    it("should return null on submit if the name is already taken", () => {
      component.nameSignal.set("Other_Policy");

      component.onAction("submit");
      expect(dialogRef.close).toHaveBeenCalledWith(null);
    });

    it("should return null when action value is null (cancel/close)", () => {
      component.onAction(null);
      expect(dialogRef.close).toHaveBeenCalledWith(null);
    });
  });

  describe("4. Cancel Flow", () => {
    it("should leave the wrapper's close button enabled", () => {
      const wrapper = fixture.debugElement.query(By.directive(MockDialogWrapperComponent))
        .componentInstance as MockDialogWrapperComponent;

      expect(wrapper.showCloseButton()).toBe(true);
    });
  });
});
