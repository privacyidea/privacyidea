/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { ComponentFixture, fakeAsync, TestBed, tick } from "@angular/core/testing";
import { ConditionsAdditionalComponent } from "./conditions-additional.component";
import { PolicyService } from "../../../../../services/policies/policies.service";

import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { AdditionalCondition } from "../../../../../services/policies/policies.service";
import { MockPolicyService } from "../../../../../../testing/mock-services/mock-policies-service";

describe("ConditionsAdditionalComponent", () => {
  let component: ConditionsAdditionalComponent;
  let fixture: ComponentFixture<ConditionsAdditionalComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionsAdditionalComponent, NoopAnimationsModule],
      providers: [
        {
          provide: PolicyService,
          useClass: MockPolicyService
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionsAdditionalComponent);

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
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, conditions });

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
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, conditions });
    fixture.detectChanges();

    component.removeCondition(0);

    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({ conditions: [] });
  });

  it("should update active state of a condition", () => {
    const conditions: AdditionalCondition[] = [
      ["userinfo", "username", "equals", "testuser", false, "condition_is_false"]
    ];
    policyServiceMock.selectedPolicy.set({ ...policyServiceMock.emptyPolicy, conditions });
    fixture.detectChanges();

    component.updateActiveState(0, true);

    expect(policyServiceMock.updateSelectedPolicy).toHaveBeenCalledWith({
      conditions: [["userinfo", "username", "equals", "testuser", false, "condition_is_false"]]
    });
  });
});
