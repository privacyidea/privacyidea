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
import { PolicyActionItemEditComponent } from "./policy-action-item-edit.component";
import { PolicyService, PolicyActionDetail } from "../../../../../../../../services/policies/policies.service";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { FormsModule } from "@angular/forms";
import { By } from "@angular/platform-browser";
import { Component, input, output } from "@angular/core";
import { CommonModule } from "@angular/common";

@Component({
  selector: "app-selector-buttons",
  standalone: true,
  template: ""
})
class MockSelectorButtonsComponent {
  values = input.required<any[]>();
  initialValue = input<any>();
  onSelect = output<any>();
}

describe("PolicyActionItemEditComponent", () => {
  let component: PolicyActionItemEditComponent;
  let fixture: ComponentFixture<PolicyActionItemEditComponent>;
  let policyServiceMock: MockPolicyService;

  const defaultAction = { name: "test_action", value: "test_value" };
  const defaultDetail: PolicyActionDetail = {
    type: "str",
    desc: "Test Description",
    value: ["val1", "val2", "val3"]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyActionItemEditComponent, FormsModule, CommonModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }, provideNoopAnimations()]
    })
      .overrideComponent(PolicyActionItemEditComponent, {
        set: {
          imports: [CommonModule, FormsModule, MockSelectorButtonsComponent]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyActionItemEditComponent);
    component = fixture.componentInstance;
    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;

    fixture.componentRef.setInput("action", defaultAction);
    fixture.componentRef.setInput("actionDetail", defaultDetail);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should correctly identify numbers", () => {
    expect(component.isNumber("123")).toBe(true);
    expect(component.isNumber(123)).toBe(true);
    expect(component.isNumber("abc")).toBe(false);
    expect(component.isNumber("")).toBe(false);
    expect(component.isNumber(null)).toBe(false);
  });

  it("should identify boolean actions correctly", () => {
    jest.spyOn(policyServiceMock, "getDetailsOfAction").mockReturnValue({ type: "bool", desc: "" });
    expect(component.isBooleanAction("test_action")).toBe(true);
  });

  it("should emit onUpdateAction when updateAction is called", () => {
    const spy = jest.spyOn(component.onUpdateAction, "emit");
    component.updateAction("new_value");
    expect(spy).toHaveBeenCalledWith("new_value");
  });

  it("should emit onRemoveAction when delete button is clicked", () => {
    const spy = jest.spyOn(component.onRemoveAction, "emit");
    const deleteBtn = fixture.debugElement.query(By.css(".delete-icon-button"));
    deleteBtn.nativeElement.click();
    expect(spy).toHaveBeenCalled();
  });
});
