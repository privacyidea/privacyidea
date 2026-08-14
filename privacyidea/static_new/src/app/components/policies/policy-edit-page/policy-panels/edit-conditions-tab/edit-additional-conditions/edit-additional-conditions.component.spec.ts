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
import { DialogService } from "@services/dialog/dialog.service";
import { AdditionalCondition, PolicyService, SectionOptionKey } from "@services/policies/policies.service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { of } from "rxjs";
import { EditAdditionalConditionsComponent } from "./edit-additional-conditions.component";

describe("EditAdditionalConditionsComponent", () => {
  let component: EditAdditionalConditionsComponent;
  let fixture: ComponentFixture<EditAdditionalConditionsComponent>;
  let dialogServiceMock: MockDialogService;

  const mockCondition: AdditionalCondition = ["token", "serial", "equals", "12345", false, "condition_is_false"];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditAdditionalConditionsComponent],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EditAdditionalConditionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", { name: "test", conditions: [mockCondition] });
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should handle condition life cycle (edit, update, save)", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");

    // Start Edit
    component.startEditCondition(mockCondition, 0);
    expect(component.conditionValue()).toBe("12345");

    // Change value
    component.conditionValue.set("67890");
    component.saveCondition();

    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        conditions: [["token", "serial", "equals", "67890", false, "condition_is_false"]]
      })
    );
  });

  it("should update active state correctly", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.updateActiveState(0, false); // Toggle to inactive

    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        conditions: [["token", "serial", "equals", "12345", false, "condition_is_false"]]
      })
    );
  });

  it("should filter available keys based on section 'token'", () => {
    component.conditionSection.set("token");

    component.conditionKey.set("ser");
    fixture.detectChanges();

    expect(component.availableKeys()).toContain("serial");
    expect(component.availableKeys()).toContain("user_id");
    expect(component.availableKeys()).not.toContain("resolver");

    component.conditionKey.set("res");
    fixture.detectChanges();

    expect(component.availableKeys()).toContain("resolver");
    expect(component.availableKeys()).not.toContain("serial");
  });

  it("should filter available keys based on section 'container'", () => {
    component.conditionSection.set("container");
    component.conditionKey.set("stat"); // User types 'stat'

    fixture.detectChanges();

    expect(component.availableKeys()).toContain("states");
    expect(component.availableKeys()).not.toContain("type");
  });

  it("should return empty available keys for unknown sections", () => {
    // Cast to any to simulate other sections if SectionOptionKey allows or for JS safety
    component.conditionSection.set("userinfo" as unknown as SectionOptionKey);
    component.conditionKey.set("any");

    fixture.detectChanges();

    expect(component.availableKeys()).toEqual([]);
  });

  it("should remove a condition and emit the updated list", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");

    // There is one mockCondition from beforeEach
    component.removeCondition(0);

    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        conditions: []
      })
    );
  });

  it("should cancel editing and reset form signals without dialog when form is not dirty", () => {
    component.startEditCondition(mockCondition, 0);
    expect(component.showAddConditionForm()).toBe(true);

    component.cancelEdit();

    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
    expect(component.showAddConditionForm()).toBe(false);
    expect(component.editIndex()).toBeNull();
    expect(component.conditionKey()).toBe("");
    expect(component.conditionSection()).toBe("");
  });

  describe("isFormDirty", () => {
    it("should return false when form is not shown", () => {
      expect(component.isFormDirty()).toBe(false);
    });

    it("should return false when add form is shown but all fields are empty", () => {
      component.showAddConditionForm.set(true);
      expect(component.isFormDirty()).toBe(false);
    });

    it("should return true when a new condition has non-empty fields", () => {
      component.showAddConditionForm.set(true);
      component.conditionSection.set("token");
      expect(component.isFormDirty()).toBe(true);
    });

    it("should return true when a new condition has conditionActive flipped from default", () => {
      component.showAddConditionForm.set(true);
      component.conditionActive.set(false);
      expect(component.isFormDirty()).toBe(true);
    });

    it("should return true when a new condition has conditionHandleMissingData changed from default", () => {
      component.showAddConditionForm.set(true);
      component.conditionHandleMissingData.set("condition_is_true");
      expect(component.isFormDirty()).toBe(true);
    });

    it("should return false when editing a condition with unchanged values", () => {
      component.startEditCondition(mockCondition, 0);
      expect(component.isFormDirty()).toBe(false);
    });

    it("should return true when editing and value has changed", () => {
      component.startEditCondition(mockCondition, 0);
      component.conditionValue.set("99999");
      expect(component.isFormDirty()).toBe(true);
    });

    it("should return true when editing and active state has changed", () => {
      component.startEditCondition(mockCondition, 0);
      component.conditionActive.set(true);
      expect(component.isFormDirty()).toBe(true);
    });
  });

  describe("cancelEdit with dirty form", () => {
    it("should open confirmation dialog when form is dirty", () => {
      component.startEditCondition(mockCondition, 0);
      component.conditionValue.set("changed");
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of(null));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(dialogServiceMock.openDialog).toHaveBeenCalled();
      expect(component.showAddConditionForm()).toBe(true);
    });

    it("should reset form after user confirms discard in dialog", () => {
      component.startEditCondition(mockCondition, 0);
      component.conditionValue.set("changed");
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("discard"));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(component.showAddConditionForm()).toBe(false);
      expect(component.editIndex()).toBeNull();
      expect(component.conditionValue()).toBe("");
    });

    it("should save and emit when user picks save-exit", () => {
      const emitSpy = jest.spyOn(component.policyEdit, "emit");
      component.startEditCondition(mockCondition, 0);
      component.conditionValue.set("changed");
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("save-exit"));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(emitSpy).toHaveBeenCalled();
      expect(component.showAddConditionForm()).toBe(false);
    });

    it("should not save when save-exit is picked but the condition is invalid", () => {
      const emitSpy = jest.spyOn(component.policyEdit, "emit");
      component.showAddConditionForm.set(true);
      // Fill in just enough to be dirty but invalid (no section / key)
      component.conditionValue.set("something");
      expect(component.canSaveCondition()).toBe(false);
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("save-exit"));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(emitSpy).not.toHaveBeenCalled();
      expect(component.showAddConditionForm()).toBe(true);
    });
  });

  describe("canSaveCondition", () => {
    it("is true when section, comparator, missingData, and key (trimmed) are all set", () => {
      component.conditionSection.set("token");
      component.conditionComparator.set("equals");
      component.conditionHandleMissingData.set("condition_is_false");
      component.conditionKey.set("serial");
      expect(component.canSaveCondition()).toBe(true);
    });

    it("is false when key is only whitespace", () => {
      component.conditionSection.set("token");
      component.conditionComparator.set("equals");
      component.conditionHandleMissingData.set("condition_is_false");
      component.conditionKey.set("   ");
      expect(component.canSaveCondition()).toBe(false);
    });

    it("is false when section is missing", () => {
      component.conditionSection.set("");
      component.conditionComparator.set("equals");
      component.conditionHandleMissingData.set("condition_is_false");
      component.conditionKey.set("serial");
      expect(component.canSaveCondition()).toBe(false);
    });
  });

  it("should not save or emit if required fields are missing", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");

    component.showAddConditionForm.set(true);
    component.conditionSection.set(""); // Missing section
    component.conditionKey.set("some-key");

    component.saveCondition();

    expect(spy).not.toHaveBeenCalled();
  });

  it("should show the add condition form when the create button is clicked", () => {
    // First, clear existing conditions to ensure the button is visible or just check the signal
    fixture.componentRef.setInput("policy", { name: "test", conditions: [] });
    fixture.detectChanges();

    const addButton = fixture.nativeElement.querySelector(".add-condition-button-container button");
    addButton.click();

    expect(component.showAddConditionForm()).toBe(true);
  });
});
