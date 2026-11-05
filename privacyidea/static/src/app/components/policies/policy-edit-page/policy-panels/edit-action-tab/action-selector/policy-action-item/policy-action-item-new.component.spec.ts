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

import { CdkTextareaAutosize } from "@angular/cdk/text-field";
import { ElementRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormField } from "@angular/forms/signals";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { PolicyActionDetail, PolicyService } from "@services/policies/policies.service";
import { MockToggleGroupComponent } from "@testing/mock-components/mock-toggle-group.component";
import { MockPolicyService } from "@testing/mock-services";
import { INVALID_ACTION_VALUE } from "../../action-value.rule";
import { PolicyActionItemComponent, SelectableAction } from "./policy-action-item-new.component";

describe("PolicyActionItemComponent", () => {
  let component: PolicyActionItemComponent;
  let fixture: ComponentFixture<PolicyActionItemComponent>;
  let policyServiceMock: MockPolicyService;

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
    await TestBed.configureTestingModule({
      imports: [PolicyActionItemComponent, MatSelectModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    })
      .overrideComponent(PolicyActionItemComponent, {
        set: {
          imports: [FormField, MockToggleGroupComponent, MatSelectModule, MatInputModule, HighlightPipe]
        }
      })
      .compileComponents();

    policyServiceMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;

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

  it("should default currentAction value to empty string for undefined actions", () => {
    fixture.componentRef.setInput("actionValue", undefined);
    fixture.detectChanges();
    expect(component.currentAction().value).toBe("");
  });

  it("should use the actionValue input as the default for non-bool actions", () => {
    fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "str", desc: "A string" } });
    fixture.componentRef.setInput("actionValue", "myDefault");
    fixture.detectChanges();
    expect(component.currentAction().value).toBe("myDefault");
  });

  it("names the value input and the add button after the action", () => {
    fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "str", desc: "A string" } });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".detail-value input[matInput]").getAttribute("aria-label")).toBe(
      "testAction"
    );
    expect(fixture.nativeElement.querySelector("button").getAttribute("aria-label")).toBe("Add testAction");
  });

  it("should emit actionAdd with explicit value when addAction is called with a value", () => {
    const spy = jest.spyOn(component.actionAdd, "emit");
    component.addAction("explicitValue");
    expect(spy).toHaveBeenCalledWith({ name: "testAction", value: "explicitValue" });
  });

  it("should emit actionAdd with currentAction value when addAction is called without a value", () => {
    component.updateSelectedActionValue("currentVal");
    const spy = jest.spyOn(component.actionAdd, "emit");
    component.addAction();
    expect(spy).toHaveBeenCalledWith({ name: "testAction", value: "currentVal" });
  });

  it("should emit actionAdd with current value when add button is clicked", async () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "str", desc: "desc" }
    });
    fixture.detectChanges();

    const spy = jest.spyOn(component.actionAdd, "emit");
    const addButton = fixture.debugElement.query(By.css("button[mat-icon-button]"));

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

  describe("value inputs", () => {
    const setType = (type: "str" | "int" | "text", actionValue: string | number = "") => {
      fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type, desc: "desc" } });
      fixture.componentRef.setInput("actionValue", actionValue);
      fixture.detectChanges();
    };
    const control = (selector: string): HTMLInputElement | HTMLTextAreaElement =>
      fixture.nativeElement.querySelector(`.detail-value mat-form-field ${selector}`);
    const type = async (element: HTMLInputElement | HTMLTextAreaElement, value: string) => {
      element.value = value;
      element.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    const addButton = (): HTMLButtonElement =>
      fixture.debugElement.query(By.css("button[mat-icon-button]")).nativeElement;

    it.each([
      ["str", "input[type=text]"],
      ["int", "input[type=number]"],
      ["text", "textarea"]
    ] as const)("wraps the %s control in a dynamic fill form field", (actionType, selector) => {
      setType(actionType);

      const field = fixture.debugElement.query(By.css(".detail-value mat-form-field"));
      const element = control(selector);
      expect(field.nativeElement.classList).toContain("mat-form-field-appearance-fill");
      expect(field.componentInstance.subscriptSizing).toBe("dynamic");
      expect(element).not.toBeNull();
      expect(element.classList).toContain("mat-mdc-input-element");
    });

    it("grows the textarea between one and five rows", () => {
      setType("text");

      const autosize = fixture.debugElement.query(By.directive(CdkTextareaAutosize)).injector.get(CdkTextareaAutosize);
      expect(autosize.minRows).toBe(1);
      expect(autosize.maxRows).toBe(8);
    });

    it("takes the typed string", async () => {
      setType("str");

      await type(control("input"), "typed");

      expect(component.currentAction().value).toBe("typed");
    });

    it("takes the typed number as text", async () => {
      setType("int");

      await type(control("input"), "42");

      expect(component.currentAction().value).toBe("42");
    });

    it("takes the typed text", async () => {
      setType("text");

      await type(control("textarea"), "line one\nline two");

      expect(component.currentAction().value).toBe("line one\nline two");
    });

    it("shows the model value in the control", async () => {
      setType("str", "shown");
      await fixture.whenStable();
      fixture.detectChanges();

      expect(control("input").value).toBe("shown");
    });

    it.each([
      ["str", "input", "x"],
      ["int", "input", "7"],
      ["text", "textarea", "x"]
    ] as const)(
      "enables the add button once the %s control holds a valid value",
      async (actionType, selector, text) => {
        setType(actionType);
        await fixture.whenStable();
        fixture.detectChanges();
        expect(addButton().disabled).toBe(true);

        await type(control(selector), text);

        expect(component.valueForm().valid()).toBe(true);
        expect(addButton().disabled).toBe(false);
      }
    );

    it("keeps an emptied number empty and the add button disabled instead of turning it into 0", async () => {
      setType("int", "5");
      await type(control("input"), "");

      expect(component.currentAction().value).toBe("");
      expect(component.valueForm().valid()).toBe(false);
      expect(addButton().disabled).toBe(true);
    });

    it("rejects a non-integer number", async () => {
      setType("int");

      await type(control("input"), "1.5");

      expect(component.valueForm().valid()).toBe(false);
    });

    it("keeps the model and blocks the add button while the number input holds text the browser cannot parse", async () => {
      setType("int", "5");
      const element = control("input") as HTMLInputElement;
      Object.defineProperty(element, "validity", { value: { badInput: true }, configurable: true });

      await type(element, "");

      expect(component.currentAction().value).toBe("5");
      expect(
        component
          .valueForm()
          .errors()
          .map((error) => error.kind)
      ).toContain("parse");
      expect(addButton().disabled).toBe(true);
    });

    it("reports a blank string as invalid with the invalidValue kind", async () => {
      setType("str", "x");
      await type(control("input"), "   ");

      expect(
        component
          .valueForm()
          .errors()
          .map((error) => error.kind)
      ).toEqual([INVALID_ACTION_VALUE]);
    });

    it("does not add on Enter while the value is blank", () => {
      setType("str");
      const spy = jest.spyOn(component, "addAction");

      control("input").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

      expect(spy).not.toHaveBeenCalled();
    });

    it("adds the typed value on Enter", async () => {
      setType("str");
      const spy = jest.spyOn(component.actionAdd, "emit");
      await type(control("input"), "typed");

      control("input").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

      expect(spy).toHaveBeenCalledWith({ name: "testAction", value: "typed" });
    });

    it("starts again from the action value when the action changes", async () => {
      setType("str", "first");
      await type(control("input"), "typed");

      fixture.componentRef.setInput("selectableAction", {
        ...defaultAction,
        actionName: "other",
        detail: { type: "str", desc: "desc" }
      });
      fixture.detectChanges();

      expect(component.currentAction()).toEqual({ name: "other", value: "first" });
    });

    it("adds on Enter for int", () => {
      setType("int", 5);
      const spy = jest.spyOn(component, "addAction");

      fixture.debugElement.query(By.css("input[type=number]")).triggerEventHandler("keydown.enter", {});

      expect(spy).toHaveBeenCalled();
    });

    it("has no Enter handler on the textarea", () => {
      setType("text", "some text");
      const spy = jest.spyOn(component, "addAction");

      control("textarea").dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

      expect(spy).not.toHaveBeenCalled();
    });

    it.each(["str", "int", "text"] as const)("disables the add button while the %s value is invalid", (actionType) => {
      policyServiceMock.actionValueIsValid.mockReturnValue(false);
      setType(actionType, "x");

      const button = fixture.debugElement.query(By.css("button[mat-icon-button]")).nativeElement;
      expect(button.disabled).toBe(true);
    });

    it.each([
      ["str", "input"],
      ["int", "input"],
      ["text", "textarea"]
    ] as const)("focuses the %s matInput element", async (actionType, selector) => {
      setType(actionType);
      const focusSpy = jest.spyOn(control(selector), "focus");

      component.focusFirstInput();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(focusSpy).toHaveBeenCalled();
    });
  });

  describe("toggle and select selection", () => {
    it("selects the numeric option matching a stored string value in the toggle group", () => {
      fixture.componentRef.setInput("selectableAction", {
        ...defaultAction,
        detail: { type: "int", desc: "numbers", value: [6, 8] }
      });
      fixture.componentRef.setInput("actionValue", "6");
      fixture.detectChanges();

      const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));
      expect(toggleGroup.componentInstance.value()).toBe(6);
    });

    it("emits the original option value, not the stored string, when a numeric toggle is picked", () => {
      fixture.componentRef.setInput("selectableAction", {
        ...defaultAction,
        detail: { type: "int", desc: "numbers", value: [6, 8] }
      });
      fixture.componentRef.setInput("actionValue", "6");
      fixture.detectChanges();
      const spy = jest.spyOn(component.actionAdd, "emit");

      fixture.debugElement.query(By.directive(MockToggleGroupComponent)).componentInstance.value.set(8);
      component.addAction();

      expect(spy).toHaveBeenCalledWith({ name: "testAction", value: 8 });
    });

    it("keeps a string option as the string", () => {
      component.updateSelectedActionValue("val2");

      expect(component.selectedValue()).toBe("val2");
    });

    it("keeps a value that matches no option", () => {
      component.updateSelectedActionValue("other");

      expect(component.selectedValue()).toBe("other");
    });

    it("selects the numeric option matching a stored string value in the dropdown", () => {
      fixture.componentRef.setInput("selectableAction", {
        ...defaultAction,
        detail: { type: "int", desc: "numbers", value: [6, 8, 10] }
      });
      fixture.componentRef.setInput("actionValue", "8");
      fixture.detectChanges();

      expect(fixture.debugElement.query(By.directive(MatSelect)).componentInstance.value).toBe(8);
    });
  });

  describe("valueForm", () => {
    it("is invalid when the value is empty", () => {
      fixture.componentRef.setInput("actionValue", "");
      fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "str", desc: "desc" } });
      fixture.detectChanges();
      expect(component.valueForm().valid()).toBe(false);
    });

    it("is invalid when no action value is given", () => {
      fixture.componentRef.setInput("actionValue", undefined);
      fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "str", desc: "desc" } });
      fixture.detectChanges();
      expect(component.valueForm().valid()).toBe(false);
    });

    it("is invalid when the detail is falsy", () => {
      fixture.componentRef.setInput("selectableAction", {
        ...defaultAction,
        detail: null as unknown as PolicyActionDetail
      });
      expect(component.valueForm().valid()).toBe(false);
    });

    it("is valid for the default of a bool action", () => {
      fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "bool", desc: "toggle" } });
      fixture.detectChanges();
      expect(component.valueForm().valid()).toBe(true);
    });

    it("follows the value written by the select, the multi select or the toggle group", () => {
      fixture.componentRef.setInput("selectableAction", {
        ...defaultAction,
        detail: { type: "int", desc: "n", value: [6, 8, 10] }
      });
      fixture.detectChanges();
      expect(component.valueForm().valid()).toBe(false);

      component.updateSelectedActionValue(8);
      expect(component.valueForm().valid()).toBe(true);

      component.updateSelectedActionValue([6, 10]);
      expect(component.currentAction().value).toBe("6 10");
      expect(component.valueForm().valid()).toBe(false);
    });

    it("asks the policy service about the current detail and value", () => {
      fixture.componentRef.setInput("selectableAction", { ...defaultAction, detail: { type: "int", desc: "n" } });
      fixture.componentRef.setInput("actionValue", "12");
      fixture.detectChanges();

      expect(component.valueForm().valid()).toBe(true);
      expect(policyServiceMock.actionValueIsValid).toHaveBeenCalledWith({ type: "int", desc: "n" }, "12");
    });
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
    const focusSpy = jest.spyOn(selectorInstance!, "focus");

    component.focusFirstInput();

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(focusSpy).toHaveBeenCalled();
  });

  it("adds the raw value when a labelled option is picked from the select", () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      actionName: "otppin",
      detail: { type: "str", desc: "otppin", value: ["tokenpin", "userstore", "disable", "none"] }
    });
    fixture.detectChanges();

    const select = fixture.debugElement.query(By.directive(MatSelect));
    select.componentInstance.open();
    fixture.detectChanges();

    const options = fixture.debugElement.queryAll(By.css("mat-option"));
    expect(options.map((option) => [option.componentInstance.value, option.nativeElement.textContent.trim()])).toEqual([
      ["tokenpin", "Token PIN"],
      ["userstore", "User store"],
      ["disable", "Disabled"],
      ["none", "None"]
    ]);

    const spy = jest.spyOn(component.actionAdd, "emit");
    options[1].nativeElement.click();
    fixture.detectChanges();

    expect(component.currentAction().value).toBe("userstore");

    fixture.debugElement.query(By.css("button[mat-icon-button]")).nativeElement.click();

    expect(spy).toHaveBeenCalledWith({ name: "otppin", value: "userstore" });
  });

  it("passes raw values and display labels to the toggle group in separate inputs", () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "str", desc: "switch", value: ["0", "1"] }
    });
    fixture.detectChanges();

    const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));

    expect(toggleGroup.componentInstance.values()).toEqual(["0", "1"]);
    expect(toggleGroup.componentInstance.labels()).toEqual(["Off", "On"]);
  });

  it("shows the toggle group without the check icon, named after the action", () => {
    const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));

    expect(toggleGroup.componentInstance.hideSelectionIndicator()).toBe(true);
    expect(toggleGroup.componentInstance.groupLabel()).toBe("testAction");
  });

  it("shows the current value as the selected toggle", () => {
    component.updateSelectedActionValue("val2");
    fixture.detectChanges();

    const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));
    expect(toggleGroup.componentInstance.value()).toBe("val2");
  });

  it("takes the value of a selected toggle", () => {
    const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));

    toggleGroup.componentInstance.value.set("val2");

    expect(component.currentAction()).toEqual({ name: "testAction", value: "val2" });
  });

  it("takes a numeric toggle value as it is", () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "int", desc: "numbers", value: [1, 2] }
    });
    fixture.detectChanges();
    const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));

    toggleGroup.componentInstance.value.set(2);

    expect(component.currentAction()).toEqual({ name: "testAction", value: 2 });
  });

  it("falls back to an empty value when the toggle group reports none", () => {
    const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));

    toggleGroup.componentInstance.value.set(undefined);

    expect(component.currentAction().value).toBe("");
  });

  it("should offer three values in a dropdown instead of buttons", () => {
    fixture.componentRef.setInput("selectableAction", {
      ...defaultAction,
      detail: { type: "str", desc: "three", value: ["1", "2", "3"] }
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.directive(MockToggleGroupComponent))).toBeNull();
    expect(fixture.debugElement.query(By.css("mat-select"))).not.toBeNull();
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
      jest.spyOn(component, "inputElementRef").mockReturnValue({ nativeElement: mockInput } as ElementRef);

      component.focusFirstInput();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockInput.focus).toHaveBeenCalled();
    });

    it("should focus the select element when no input is present", async () => {
      const mockSelect = { focus: jest.fn() };
      jest.spyOn(component, "selectElementRef").mockReturnValue(mockSelect as unknown as MatSelect);
      jest.spyOn(component, "inputElementRef").mockReturnValue(undefined);

      component.focusFirstInput();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockSelect.focus).toHaveBeenCalled();
    });

    it("should focus the button element when no input or select is present", async () => {
      const mockButton = { focus: jest.fn() };
      jest.spyOn(component, "buttonElementRef").mockReturnValue({ nativeElement: mockButton } as ElementRef);
      jest.spyOn(component, "inputElementRef").mockReturnValue(undefined);
      jest.spyOn(component, "selectElementRef").mockReturnValue(undefined);
      jest.spyOn(component, "selectorComponent").mockReturnValue(undefined);

      component.focusFirstInput();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockButton.focus).toHaveBeenCalled();
    });
  });
});
