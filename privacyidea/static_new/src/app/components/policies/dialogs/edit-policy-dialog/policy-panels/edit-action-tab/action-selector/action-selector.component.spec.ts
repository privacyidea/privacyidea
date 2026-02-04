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
import { ActionSelectorComponent } from "./action-selector.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { By } from "@angular/platform-browser";
import { SelectorButtonsComponent } from "../selector-buttons/selector-buttons.component";
import { MockPolicyService } from "../../../../../../../../testing/mock-services/mock-policies-service";
import { PolicyService } from "../../../../../../../services/policies/policies.service";

describe("ActionSelectorComponent", () => {
  let component: ActionSelectorComponent;
  let fixture: ComponentFixture<ActionSelectorComponent>;
  let policyServiceMock: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ActionSelectorComponent, NoopAnimationsModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(ActionSelectorComponent);
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    component = fixture.componentInstance;
    jest.spyOn(policyServiceMock.actionFilter, "set");
    jest.spyOn(policyServiceMock.selectedActionGroup, "set");
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display available actions", () => {
    policyServiceMock.actionNamesOfSelectedGroup.set(["action1", "action2"]);
    fixture.detectChanges();
    const actionElements = fixture.nativeElement.querySelectorAll(".policy-action-item");
    expect(actionElements.length).toBe(2);
    expect(actionElements[0].textContent).toContain("action1");
    expect(actionElements[1].textContent).toContain("action2");
  });

  it("should select an action on click", () => {
    const actions = ["action1", "action2"];
    policyServiceMock.actionNamesOfSelectedGroup.set(actions);
    fixture.detectChanges();

    const actionElement = fixture.nativeElement.querySelectorAll(".policy-action-item");
    actionElement[1].click();

    expect(policyServiceMock.selectActionByName).toHaveBeenCalledWith(actions[1]);
  });

  it("should apply selected class to selected action", () => {
    const actions = ["action1", "action2"];
    policyServiceMock.actionNamesOfSelectedGroup.set(actions);
    policyServiceMock.selectedAction.set({ name: "action1", value: "" });
    fixture.detectChanges();

    const actionElements = fixture.nativeElement.querySelectorAll(".policy-action-item");
    expect(actionElements[0].classList).toContain("policy-action-item-selected");
    expect(actionElements[1].classList).not.toContain("policy-action-item-selected");
  });

  it("should filter actions based on input", () => {
    fixture.detectChanges();
    const input: HTMLInputElement = fixture.nativeElement.querySelector(".search-input");

    input.value = "test";
    input.dispatchEvent(new Event("input"));

    const actionFilter = policyServiceMock.actionFilter();
    expect(actionFilter).toBe("test");

    expect(policyServiceMock.actionFilter.set).toHaveBeenCalledWith("test");
  });

  it("should show group selector if more than one group exists", () => {
    policyServiceMock.groupNamesOfSelectedScope.set(["group1", "group2"]);
    fixture.detectChanges();
    const groupSelector = fixture.nativeElement.querySelector("app-selector-buttons");
    expect(groupSelector).toBeTruthy();
  });

  it("should not show group selector if only one group exists", () => {
    policyServiceMock.groupNamesOfSelectedScope.set(["group1"]);
    fixture.detectChanges();
    const groupSelector = fixture.nativeElement.querySelector("app-selector-buttons");
    expect(groupSelector).toBeFalsy();
  });

  it("should call service when group is selected", () => {
    policyServiceMock.groupNamesOfSelectedScope.set(["group1", "group2"]);
    fixture.detectChanges();
    const groupSelector = fixture.debugElement.query(By.directive(SelectorButtonsComponent));
    groupSelector.triggerEventHandler("onSelect", "group2");
    expect(policyServiceMock.selectedActionGroup.set).toHaveBeenCalledWith("group2");
  });
});
