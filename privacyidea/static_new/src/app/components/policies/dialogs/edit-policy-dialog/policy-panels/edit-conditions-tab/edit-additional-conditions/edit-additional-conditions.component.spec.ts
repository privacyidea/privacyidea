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
import { EditAdditionalConditionsComponent } from "./edit-additional-conditions.component";
import { PolicyService, AdditionalCondition } from "../../../../../../../services/policies/policies.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { provideNoopAnimations } from "@angular/platform-browser/animations";

describe("EditAdditionalConditionsComponent", () => {
  let component: EditAdditionalConditionsComponent;
  let fixture: ComponentFixture<EditAdditionalConditionsComponent>;

  const mockCondition: AdditionalCondition = ["token", "serial", "equals", "12345", false, "condition_is_false"];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditAdditionalConditionsComponent],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }, provideNoopAnimations()]
    }).compileComponents();

    fixture = TestBed.createComponent(EditAdditionalConditionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", { name: "test", conditions: [mockCondition] });
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
        conditions: [["token", "serial", "equals", "12345", true, "condition_is_false"]]
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
    component.conditionSection.set("userinfo" as any);
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

  it("should cancel editing and reset form signals", () => {
    component.startEditCondition(mockCondition, 0);
    expect(component.showAddConditionForm()).toBe(true);

    component.cancelEdit();

    expect(component.showAddConditionForm()).toBe(false);
    expect(component.editIndex()).toBeNull();
    expect(component.conditionKey()).toBe("");
    expect(component.conditionSection()).toBe("");
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
