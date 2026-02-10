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
import { By } from "@angular/platform-browser";

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
});
