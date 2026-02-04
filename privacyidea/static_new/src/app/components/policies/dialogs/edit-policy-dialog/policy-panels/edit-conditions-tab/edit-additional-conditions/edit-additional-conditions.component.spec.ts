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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockPolicyService } from "../../../../../../../../testing/mock-services/mock-policies-service";
import { PolicyService, AdditionalCondition } from "../../../../../../../services/policies/policies.service";
import { EditAdditionalConditionsComponent } from "./edit-additional-conditions.component";

describe("ConditionsAdditionalComponent", () => {
  let component: EditAdditionalConditionsComponent;
  let fixture: ComponentFixture<EditAdditionalConditionsComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditAdditionalConditionsComponent, NoopAnimationsModule],
      providers: [
        {
          provide: PolicyService,
          useClass: MockPolicyService
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EditAdditionalConditionsComponent);

    component = fixture.componentInstance;
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display additional conditions", () => {
    const conditions: AdditionalCondition[] = [
      ["userinfo", "username", "equals", "testuser", false, "condition_is_false"],
      ["token", "hour", ">", "12", true, "raise_error"]
    ];

    policyServiceMock.selectedPolicyHasAdditionalConditions.set(true);
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.getEmptyPolicy, conditions });

    fixture.detectChanges();

    const conditionElements = fixture.nativeElement.querySelectorAll(".additional-condition-row");

    expect(conditionElements.length).toBe(conditions.length);
    expect(conditionElements[0].textContent).toContain("userinfo");
    expect(conditionElements[1].textContent).toContain("raise_error");
  });

  it("should add a new condition", () => {
    policyServiceMock.isEditMode.set(true);
    fixture.detectChanges();

    component.conditionSection.set("userinfo");
    component.conditionKey.set("username");
    component.conditionComparator.set("equals");
    component.conditionValue.set("newuser");
    component.conditionActive.set(true);
    component.conditionHandleMissingData.set("condition_is_false");

    component.saveCondition();

    const conditions: AdditionalCondition[] = [
      ["userinfo", "username", "equals", "newuser", true, "condition_is_false"]
    ];

    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({
      conditions: conditions
    });
  });

  it("should remove a condition", () => {
    const conditions: AdditionalCondition[] = [
      ["userinfo", "username", "equals", "testuser", false, "condition_is_false"]
    ];
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.getEmptyPolicy, conditions });
    fixture.detectChanges();

    component.removeCondition(0);

    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ conditions: [] });
  });

  it("should update active state of a condition", () => {
    const conditions: AdditionalCondition[] = [
      ["userinfo", "username", "equals", "testuser", false, "condition_is_false"]
    ];
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.getEmptyPolicy, conditions });
    fixture.detectChanges();

    component.updateActiveState(0, true);

    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({
      conditions: [["userinfo", "username", "equals", "testuser", false, "condition_is_false"]]
    });
  });
});
