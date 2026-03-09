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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { CopyPolicyDialogComponent } from "./copy-policy-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { Component, input, output } from "@angular/core";
import { ReactiveFormsModule } from "@angular/forms";

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
  actions = input.required<any[]>();
  close = output<void>();
  onAction = output<any>();
}

describe("CopyPolicyDialogComponent", () => {
  let component: CopyPolicyDialogComponent;
  let fixture: ComponentFixture<CopyPolicyDialogComponent>;
  let dialogRef: MockMatDialogRef;
  const initialPolicyName = "Original_Policy";

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CopyPolicyDialogComponent, NoopAnimationsModule, ReactiveFormsModule],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: initialPolicyName }
      ]
    })
      .overrideComponent(CopyPolicyDialogComponent, {
        set: {
          imports: [MockDialogWrapperComponent, ReactiveFormsModule]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(CopyPolicyDialogComponent);
    component = fixture.componentInstance;
    dialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef;
    fixture.detectChanges();
  });

  describe("1. Validator Logic", () => {
    it("should reject unchanged names with 'notChanged' error", () => {
      component.nameControl.setValue(initialPolicyName);
      expect(component.nameControl.hasError("notChanged")).toBe(true);
      expect(component.nameControl.valid).toBe(false);
    });

    it("should be valid when the name is changed", () => {
      component.nameControl.setValue("Modified_Policy_Name");
      expect(component.nameControl.hasError("notChanged")).toBe(false);
      expect(component.nameControl.valid).toBe(true);
    });

    it("should reject empty names (required)", () => {
      component.nameControl.setValue("");
      expect(component.nameControl.hasError("required")).toBe(true);
    });
  });

  describe("2. UI Actions State", () => {
    it("should disable confirm/submit action when the form is invalid", () => {
      component.nameControl.setValue(initialPolicyName);
      // Trigger statusChanges for the signal
      component.nameControl.updateValueAndValidity();
      fixture.detectChanges();

      const submitAction = component.actions().find((a) => a.value === "submit");
      expect(submitAction?.disabled).toBe(true);
    });

    it("should enable confirm/submit action when the form is valid", () => {
      component.nameControl.setValue("New_Unique_Name");
      component.nameControl.updateValueAndValidity();
      fixture.detectChanges();

      const submitAction = component.actions().find((a) => a.value === "submit");
      expect(submitAction?.disabled).toBe(false);
    });
  });

  describe("3. onAction Flow", () => {
    it("should return the new name only when valid on submit", () => {
      const newName = "Valid_New_Name";
      component.nameControl.setValue(newName);

      component.onAction("submit");
      expect(dialogRef.close).toHaveBeenCalledWith(newName);
    });

    it("should return null on submit if the form is invalid", () => {
      component.nameControl.setValue(initialPolicyName);

      component.onAction("submit");
      expect(dialogRef.close).toHaveBeenCalledWith(null);
    });

    it("should return null when action value is null (cancel/close)", () => {
      component.onAction(null);
      expect(dialogRef.close).toHaveBeenCalledWith(null);
    });
  });
});
