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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
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

  /** Writes to the model without a control, so the fields stay pristine. */
  const setCondition = (values: Partial<ReturnType<typeof component.condition>>) =>
    component.condition.update((condition) => ({ ...condition, ...values }));

  const fillRequiredFields = () =>
    setCondition({ section: "token", comparator: "equals", handleMissingData: "condition_is_false", key: "serial" });

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };

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

  /** A closed select panel stays in the overlay until its animation ends, which would shadow the next panel. */
  const clearOverlay = () =>
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));

  afterEach(clearOverlay);

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should handle condition life cycle (edit, update, save)", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");

    // Start Edit
    component.startEditCondition(mockCondition, 0);
    expect(component.condition().value).toBe("12345");

    // Change value
    setCondition({ value: "67890" });
    component.saveCondition();

    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        conditions: [["token", "serial", "equals", "67890", false, "condition_is_false"]]
      })
    );
  });

  it("should append a new condition and trim its key", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.showAddConditionForm.set(true);
    fillRequiredFields();
    setCondition({ key: "  serial  ", value: "x", active: false });

    component.saveCondition();

    expect(spy).toHaveBeenCalledWith({
      conditions: [mockCondition, ["token", "serial", "equals", "x", false, "condition_is_false"]]
    });
    expect(component.showAddConditionForm()).toBe(false);
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

  it("should mirror an active toggle of the condition being edited without making the form dirty", () => {
    component.startEditCondition(mockCondition, 0);

    component.updateActiveState(0, true);

    expect(component.condition().active).toBe(true);
    expect(component.isFormDirty()).toBe(false);
  });

  it("should leave the form alone when another condition is toggled", () => {
    component.startEditCondition(mockCondition, 0);

    component.updateActiveState(1, true);

    expect(component.condition().active).toBe(false);
  });

  it("should filter available keys based on section 'token'", () => {
    setCondition({ section: "token", key: "ser" });
    fixture.detectChanges();

    expect(component.availableKeys()).toContain("serial");
    expect(component.availableKeys()).toContain("user_id");
    expect(component.availableKeys()).not.toContain("resolver");

    setCondition({ key: "res" });
    fixture.detectChanges();

    expect(component.availableKeys()).toContain("resolver");
    expect(component.availableKeys()).not.toContain("serial");
  });

  it("should filter available keys based on section 'container'", () => {
    setCondition({ section: "container", key: "stat" }); // User types 'stat'

    fixture.detectChanges();

    expect(component.availableKeys()).toContain("states");
    expect(component.availableKeys()).not.toContain("type");
  });

  it("should return empty available keys for unknown sections", () => {
    // Cast to any to simulate other sections if SectionOptionKey allows or for JS safety
    setCondition({ section: "userinfo" as unknown as SectionOptionKey, key: "any" });

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
    expect(component.condition().key).toBe("");
    expect(component.condition().section).toBe("");
  });

  describe("isFormDirty", () => {
    const openDirtyEdit = async () => {
      component.startEditCondition(mockCondition, 0);
      await flush();
      const valueInput = fixture.debugElement.queryAll(By.css(".new-condition-form input"))[1].nativeElement;
      valueInput.value = "99999";
      valueInput.dispatchEvent(new Event("input"));
    };

    it("should return false when form is not shown", () => {
      expect(component.isFormDirty()).toBe(false);
    });

    it("should return false when add form is shown but nothing was entered", () => {
      component.showAddConditionForm.set(true);
      expect(component.isFormDirty()).toBe(false);
    });

    it("should stay false for values that the model received without a control", () => {
      component.showAddConditionForm.set(true);
      setCondition({ section: "token", active: false, handleMissingData: "condition_is_true" });
      expect(component.isFormDirty()).toBe(false);
    });

    it("should return false when editing a condition with unchanged values", () => {
      component.startEditCondition(mockCondition, 0);
      expect(component.isFormDirty()).toBe(false);
    });

    it("should become true when a value is typed", async () => {
      await openDirtyEdit();
      expect(component.isFormDirty()).toBe(true);
      expect(component.condition().value).toBe("99999");
    });

    it("should become true when only a select changes", async () => {
      component.showAddConditionForm.set(true);
      await flush();
      expect(component.isFormDirty()).toBe(false);

      await pickOption(0, 5);

      expect(component.condition().section).toBe("token");
      expect(component.isFormDirty()).toBe(true);
    });

    it("should become true when the key is typed", async () => {
      component.showAddConditionForm.set(true);
      await flush();

      const keyInput = fixture.debugElement.queryAll(By.css(".new-condition-form input"))[0].nativeElement;
      keyInput.value = "serial";
      keyInput.dispatchEvent(new Event("input"));

      expect(component.condition().key).toBe("serial");
      expect(component.isFormDirty()).toBe(true);
    });

    it("should be false again after loading another condition", async () => {
      await openDirtyEdit();
      expect(component.isFormDirty()).toBe(true);

      component.startEditCondition(mockCondition, 0);

      expect(component.isFormDirty()).toBe(false);
    });
  });

  /** The selects of the form in template order: section, if data missing, comparator. */
  const pickOption = async (selectIndex: number, optionIndex: number) => {
    const matSelect = fixture.debugElement.queryAll(By.directive(MatSelect))[selectIndex]
      .componentInstance as MatSelect;
    matSelect.open();
    await flush();
    (document.querySelectorAll("mat-option")[optionIndex] as HTMLElement).click();
    await flush();
    clearOverlay();
  };

  describe("cancelEdit with dirty form", () => {
    const makeDirty = async () => {
      component.startEditCondition(mockCondition, 0);
      await flush();
      const valueInput = fixture.debugElement.queryAll(By.css(".new-condition-form input"))[1].nativeElement;
      valueInput.value = "changed";
      valueInput.dispatchEvent(new Event("input"));
    };

    it("should open confirmation dialog when form is dirty", async () => {
      await makeDirty();
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of(null));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ data: expect.objectContaining({ allowSaveExit: true, saveExitDisabled: false }) })
      );
      expect(component.showAddConditionForm()).toBe(true);
    });

    it("should reset form after user confirms discard in dialog", async () => {
      await makeDirty();
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("discard"));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(component.showAddConditionForm()).toBe(false);
      expect(component.editIndex()).toBeNull();
      expect(component.condition().value).toBe("");
      expect(component.isFormDirty()).toBe(false);
    });

    it("should save and emit when user picks save-exit", async () => {
      const emitSpy = jest.spyOn(component.policyEdit, "emit");
      await makeDirty();
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("save-exit"));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(emitSpy).toHaveBeenCalledWith({
        conditions: [["token", "serial", "equals", "changed", false, "condition_is_false"]]
      });
      expect(component.showAddConditionForm()).toBe(false);
    });

    it("should not save when save-exit is picked but the condition is invalid", async () => {
      const emitSpy = jest.spyOn(component.policyEdit, "emit");
      component.showAddConditionForm.set(true);
      await flush();
      // Fill in just enough to be dirty but invalid (no section / key)
      const valueInput = fixture.debugElement.queryAll(By.css(".new-condition-form input"))[1].nativeElement;
      valueInput.value = "something";
      valueInput.dispatchEvent(new Event("input"));
      expect(component.canSaveCondition()).toBe(false);
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("save-exit"));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);

      component.cancelEdit();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ data: expect.objectContaining({ allowSaveExit: false, saveExitDisabled: true }) })
      );
      expect(emitSpy).not.toHaveBeenCalled();
      expect(component.showAddConditionForm()).toBe(true);
    });
  });

  describe("canSaveCondition", () => {
    const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((e) => e.kind);

    it("is true when section, comparator, missingData, and key are all set", () => {
      fillRequiredFields();
      expect(component.canSaveCondition()).toBe(true);
    });

    it("is true when the value is empty", () => {
      fillRequiredFields();
      setCondition({ value: "" });
      expect(component.canSaveCondition()).toBe(true);
    });

    it("is false when key is only whitespace", () => {
      fillRequiredFields();
      setCondition({ key: "   " });
      expect(component.canSaveCondition()).toBe(false);
      expect(kinds(component.conditionForm.key())).toEqual(["required"]);
    });

    it("is false when the key is empty", () => {
      fillRequiredFields();
      setCondition({ key: "" });
      expect(kinds(component.conditionForm.key())).toEqual(["required"]);
      expect(component.canSaveCondition()).toBe(false);
    });

    it("is false when section is missing", () => {
      fillRequiredFields();
      setCondition({ section: "" });
      expect(component.canSaveCondition()).toBe(false);
      expect(kinds(component.conditionForm.section())).toEqual(["required"]);
    });

    it("is false when the comparator is missing", () => {
      fillRequiredFields();
      setCondition({ comparator: "" });
      expect(component.canSaveCondition()).toBe(false);
      expect(kinds(component.conditionForm.comparator())).toEqual(["required"]);
    });

    it("is false when the handling of missing data is missing", () => {
      fillRequiredFields();
      setCondition({ handleMissingData: "" });
      expect(component.canSaveCondition()).toBe(false);
      expect(kinds(component.conditionForm.handleMissingData())).toEqual(["required"]);
    });

    it("starts with 'condition is false' for missing data and an active condition", () => {
      expect(component.condition().handleMissingData).toBe("condition_is_false");
      expect(component.condition().active).toBe(true);
      expect(component.conditionForm.handleMissingData().valid()).toBe(true);
    });
  });

  it("should not save or emit if required fields are missing", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");

    component.showAddConditionForm.set(true);
    setCondition({ section: "", key: "some-key" }); // Missing section

    component.saveCondition();

    expect(spy).not.toHaveBeenCalled();
    expect(component.showAddConditionForm()).toBe(true);
  });

  it("should show the add condition form when the create button is clicked", () => {
    // First, clear existing conditions to ensure the button is visible or just check the signal
    fixture.componentRef.setInput("policy", { name: "test", conditions: [] });
    fixture.detectChanges();

    const addButton = fixture.nativeElement.querySelector(".add-condition-button-container button");
    addButton.click();

    expect(component.showAddConditionForm()).toBe(true);
  });

  describe("form", () => {
    const saveButton = (): HTMLButtonElement =>
      fixture.debugElement.query(By.css(".form-actions .action-button-primary")).nativeElement;
    const errorTexts = (): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((e) =>
        (e as HTMLElement).textContent!.trim()
      );

    beforeEach(async () => {
      component.showAddConditionForm.set(true);
      await flush();
    });

    it("should disable the save button while a required field is empty", () => {
      expect(saveButton().disabled).toBe(true);
    });

    it("should enable the save button once every required field is filled", async () => {
      fillRequiredFields();
      await flush();

      expect(saveButton().disabled).toBe(false);
    });

    it("should write the picked options of the selects to the model", async () => {
      await pickOption(0, 3);
      await pickOption(1, 2);

      expect(component.condition().section).toBe("container");
      expect(component.condition().handleMissingData).toBe("condition_is_true");
    });

    it("should write the picked comparator to the model", async () => {
      await pickOption(2, 2);

      expect(component.condition().comparator).toBe("equals");
    });

    it("should show the selected options in the selects", async () => {
      fillRequiredFields();
      await flush();

      const selects = fixture.debugElement
        .queryAll(By.directive(MatSelect))
        .map((s) => s.componentInstance as MatSelect);
      expect(selects.map((select) => select.value)).toEqual(["token", "condition_is_false", "equals"]);
    });

    it("should write a typed value to the model", () => {
      const valueInput = fixture.debugElement.queryAll(By.css(".new-condition-form input"))[1].nativeElement;
      valueInput.value = "abc";
      valueInput.dispatchEvent(new Event("input"));

      expect(component.condition().value).toBe("abc");
    });

    it("should offer the keys of the section as autocomplete options", async () => {
      setCondition({ section: "token", key: "ser" });
      await flush();
      const keyInput = fixture.debugElement.queryAll(By.css(".new-condition-form input"))[0].nativeElement;

      keyInput.focus();
      keyInput.dispatchEvent(new Event("focusin"));
      await flush();

      const options = Array.from(document.querySelectorAll("mat-option")).map((o) => o.textContent!.trim());
      expect(options).toEqual(expect.arrayContaining(["serial", "user_id"]));
    });

    it("should write a picked key suggestion to the model", async () => {
      setCondition({ section: "token", key: "ser" });
      await flush();
      const keyInput = fixture.debugElement.queryAll(By.css(".new-condition-form input"))[0].nativeElement;
      keyInput.focus();
      keyInput.dispatchEvent(new Event("focusin"));
      await flush();

      const serial = Array.from(document.querySelectorAll("mat-option")).find(
        (o) => o.textContent!.trim() === "serial"
      ) as HTMLElement;
      serial.click();
      await flush();

      expect(component.condition().key).toBe("serial");
      expect(component.isFormDirty()).toBe(true);
    });

    it("should show no message before a field was touched", () => {
      expect(errorTexts()).toEqual([]);
    });

    it("should show a message per missing required field once the fields are touched", async () => {
      component.conditionForm().markAsTouched();
      component.conditionForm.section().markAsTouched();
      component.conditionForm.comparator().markAsTouched();
      component.conditionForm.key().markAsTouched();
      component.conditionForm.handleMissingData().markAsTouched();
      setCondition({ handleMissingData: "" });
      await flush();

      expect(errorTexts()).toEqual([
        "Section is required.",
        "If Data Missing is required.",
        "Key is required.",
        "Comparator is required."
      ]);
    });

    it("should save the condition with the save button", async () => {
      const spy = jest.spyOn(component.policyEdit, "emit");
      fillRequiredFields();
      await flush();

      saveButton().click();

      expect(spy).toHaveBeenCalledWith({
        conditions: [mockCondition, ["token", "serial", "equals", "", true, "condition_is_false"]]
      });
    });
  });
});
