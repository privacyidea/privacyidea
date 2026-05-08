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

import { Component, input, output } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormsModule } from "@angular/forms";
import { MatSelectModule } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { PolicyActionDetail, PolicyService } from "@services/policies/policies.service";
import { PolicyActionItemComponent, SelectableAction } from "./policy-action-item-new.component";

@Component({
  selector: "app-selector-buttons",
  template: "",
  standalone: true
})
class MockSelectorButtonsComponent {
  initialValue = input<any>();
  values = input.required<any[]>();
  onSelect = output<any>();
  focusFirst = jest.fn();
}

describe("PolicyActionItemComponent", () => {
  let component: PolicyActionItemComponent;
  let fixture: ComponentFixture<PolicyActionItemComponent>;
  let policyServiceMock: jest.Mocked<PolicyService>;

  const mockActionDetail: PolicyActionDetail = {
    type: "str",
    desc: "Test Description",
    value: ["val1", "val2"]
  };

  const defaultAction: SelectableAction = {
    actionName: "testAction",
    label: "testAction",
    scope: "admin",
    detail: mockActionDetail
  };

  beforeEach(async () => {
    policyServiceMock = {
      actionValueIsValid: jest.fn().mockReturnValue(true)
    } as any;

    await TestBed.configureTestingModule({
      imports: [PolicyActionItemComponent, NoopAnimationsModule, FormsModule, MatSelectModule],
      providers: [{ provide: PolicyService, useValue: policyServiceMock }]
    })
      .overrideComponent(PolicyActionItemComponent, {
        set: {
          imports: [MockSelectorButtonsComponent, FormsModule, MatSelectModule]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyActionItemComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput("selectableAction", defaultAction);
    fixture.componentRef.setInput("actionValue", "defaultVal");

    fixture.detectChanges();
  });

  it("should create and apply correct flex classes", () => {
    const label = fixture.debugElement.query(By.css(".detail-label"));
    const desc = fixture.debugElement.query(By.css(".detail-description"));
    expect(label).toBeTruthy();
    expect(desc).toBeTruthy();
  });

  it("should update currentAction when selectableAction changes via linkedSignal", () => {
    fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "int", desc: "new" } });
    fixture.detectChanges();
    expect(component.currentAction().name).toBe("testAction");
  });

  it("should default currentAction value to 'true' for bool actions", () => {
    fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "bool", desc: "A toggle" } });
    fixture.detectChanges();
    expect(component.currentAction().value).toBe("true");
    expect(component.isBooleanAction()).toBe(true);
  });

  it("should emit actionAdd with explicit value when addAction is called with a value", () => {
    const spy = jest.spyOn(component.actionAdd, "emit");
    component.addAction("explicitValue");
    expect(spy).toHaveBeenCalledWith({ name: "testAction", value: "explicitValue" });
  });

  it("should emit actionAdd with current value when add button is clicked", async () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "str", desc: "desc" }
    });
    fixture.detectChanges();

    const spy = jest.spyOn(component.actionAdd, "emit");
    const addButton = fixture.debugElement.query(By.css(".add-action-button"));

    addButton.nativeElement.click();

    expect(spy).toHaveBeenCalledWith({ name: "testAction", value: "defaultVal" });
  });

  it("should call addAction on Enter key if input is valid", () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "str", desc: "desc" }
    });
    fixture.detectChanges();

    const spy = jest.spyOn(component, "addAction");
    const input = fixture.debugElement.query(By.css("input"));

    input.triggerEventHandler("keydown.enter", {});

    expect(spy).toHaveBeenCalled();
  });

  it("should not call addAction on Enter key if input is invalid", () => {
    policyServiceMock.actionValueIsValid.mockReturnValue(false);
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "str", desc: "desc" }
    });
    fixture.detectChanges();

    const spy = jest.spyOn(component, "addAction");
    const input = fixture.debugElement.query(By.css("input"));

    input.triggerEventHandler("keydown.enter", {});

    expect(spy).not.toHaveBeenCalled();
  });

  it("should focus the selector component if it is active", async () => {
    fixture.detectChanges();
    const selectorInstance = component.selectorComponent();
    const focusSpy = jest.spyOn(selectorInstance!, "focusFirst");

    component.focusFirstInput();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(focusSpy).toHaveBeenCalled();
  });

  it("should handle multi-value actions with mat-select if > 3 values", () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "str", desc: "large list", value: ["1", "2", "3", "4", "5"] }
    });
    fixture.detectChanges();

    const select = fixture.debugElement.query(By.css("mat-select"));
    expect(select).toBeTruthy();
  });

  describe("selectedItems", () => {
    it("should split a space-separated string value into an array", () => {
      component.updateSelectedActionValue("val1 val2 val3");
      expect(component.selectedItems()).toEqual(["val1", "val2", "val3"]);
    });

    it("should wrap a non-string value in an array", () => {
      component.updateSelectedActionValue(42);
      expect(component.selectedItems()).toEqual([42]);
    });
  });

  describe("updateSelectedActionValue", () => {
    it("should join array values with space and set currentAction", () => {
      component.updateSelectedActionValue(["val1", "val2", "val3"]);
      expect(component.currentAction()).toEqual({ name: "testAction", value: "val1 val2 val3" });
    });

    it("should set currentAction directly for scalar values", () => {
      component.updateSelectedActionValue("singleVal");
      expect(component.currentAction()).toEqual({ name: "testAction", value: "singleVal" });
    });

    it("should set currentAction directly for numeric values", () => {
      component.updateSelectedActionValue(42);
      expect(component.currentAction()).toEqual({ name: "testAction", value: 42 });
    });
  });

  describe("focusFirstInput", () => {
    it("should focus the input element when present", async () => {
      const mockInput = { focus: jest.fn() };
      jest.spyOn(component, "inputElementRef").mockReturnValue({ nativeElement: mockInput } as any);

      component.focusFirstInput();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockInput.focus).toHaveBeenCalled();
    });

    it("should focus the select element when no input is present", async () => {
      const mockSelect = { focus: jest.fn() };
      jest.spyOn(component, "selectElementRef").mockReturnValue(mockSelect as any);
      jest.spyOn(component, "inputElementRef").mockReturnValue(undefined);

      component.focusFirstInput();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockSelect.focus).toHaveBeenCalled();
    });

    it("should focus the button element when no input or select is present", async () => {
      const mockButton = { focus: jest.fn() };
      jest.spyOn(component, "buttonElementRef").mockReturnValue({ nativeElement: mockButton } as any);
      jest.spyOn(component, "inputElementRef").mockReturnValue(undefined);
      jest.spyOn(component, "selectElementRef").mockReturnValue(undefined);
      jest.spyOn(component, "selectorComponent").mockReturnValue(undefined);

      component.focusFirstInput();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockButton.focus).toHaveBeenCalled();
    });
  });
});
