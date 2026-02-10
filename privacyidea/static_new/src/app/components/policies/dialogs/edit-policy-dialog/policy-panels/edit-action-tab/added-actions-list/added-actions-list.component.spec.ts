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
import { AddedActionsListComponent } from "./added-actions-list.component";
import { PolicyService } from "../../../../../../../services/policies/policies.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { Component, input, output } from "@angular/core";
import { By } from "@angular/platform-browser";

@Component({
  selector: "app-policy-action-item-edit",
  standalone: true,
  template: "<div></div>"
})
class MockPolicyActionItemEditComponent {
  action = input.required<{ name: string; value: any }>();
  actionDetail = input.required<any>();
  onRemoveAction = output<void>();
  onUpdateAction = output<any>();
}

describe("AddedActionsListComponent", () => {
  let component: AddedActionsListComponent;
  let fixture: ComponentFixture<AddedActionsListComponent>;
  let policyServiceMock: MockPolicyService;

  const mockActions = [
    { name: "action1", value: "val1" },
    { name: "action2", value: true }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddedActionsListComponent],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }, provideNoopAnimations()]
    })
      .overrideComponent(AddedActionsListComponent, {
        set: {
          imports: [MockPolicyActionItemEditComponent]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(AddedActionsListComponent);
    component = fixture.componentInstance;
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;

    fixture.componentRef.setInput("actions", mockActions);
    fixture.componentRef.setInput("isEditMode", true);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render a list of actions", () => {
    const items = fixture.debugElement.queryAll(By.directive(MockPolicyActionItemEditComponent));
    expect(items.length).toBe(2);
  });

  it("should emit updated actions when an action is removed", () => {
    const spy = jest.spyOn(component.actionsChange, "emit");
    component.removeActionFromSelectedPolicy("action1");
    expect(spy).toHaveBeenCalledWith([{ name: "action2", value: true }]);
  });

  it("should emit updated actions when an action value is updated", () => {
    const spy = jest.spyOn(component.actionsChange, "emit");
    component.updateActionInSelectedPolicy("action1", "new_value");
    expect(spy).toHaveBeenCalledWith([
      { name: "action1", value: "new_value" },
      { name: "action2", value: true }
    ]);
  });

  it("should identify boolean actions via policyService", () => {
    const spy = jest.spyOn(policyServiceMock, "getDetailsOfAction").mockReturnValue({ type: "bool", desc: "" });
    const result = component.isBooleanAction("action2");
    expect(spy).toHaveBeenCalledWith("action2");
    expect(result).toBe(true);
  });

  it("should call actionsChange when toggle changes", () => {
    const spy = jest.spyOn(component.actionsChange, "emit");
    component.onToggleChange("action2", false);
    expect(spy).toHaveBeenCalledWith([
      { name: "action1", value: "val1" },
      { name: "action2", value: false }
    ]);
  });
});
