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

import { CommonModule } from "@angular/common";
import { CdkTextareaAutosize } from "@angular/cdk/text-field";
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { PolicyActionDetail, PolicyService } from "@services/policies/policies.service";
import { MockToggleGroupComponent } from "@testing/mock-components/mock-toggle-group.component";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { INVALID_ACTION_VALUE } from "../../action-value.rule";
import { PolicyActionItemEditComponent } from "./policy-action-item-edit.component";

describe("PolicyActionItemEditComponent", () => {
  let component: PolicyActionItemEditComponent;
  let fixture: ComponentFixture<PolicyActionItemEditComponent>;
  const defaultAction = { name: "test_action", value: "test_value" };
  const defaultDetail: PolicyActionDetail = {
    type: "str",
    desc: "Test Description",
    value: ["val1", "val2", "val3"]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyActionItemEditComponent, CommonModule],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    })
      .overrideComponent(PolicyActionItemEditComponent, {
        set: {
          imports: [
            CommonModule,
            FormField,
            MockToggleGroupComponent,
            MatButtonModule,
            MatIconModule,
            MatFormFieldModule,
            MatInputModule,
            MatSelectModule,
            HighlightPipe
          ]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PolicyActionItemEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("action", defaultAction);
    fixture.componentRef.setInput("actionDetail", defaultDetail);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should identify boolean actions correctly", () => {
    fixture.componentRef.setInput("actionDetail", { type: "bool", desc: "" });
    fixture.detectChanges();
    expect(component.isBooleanAction()).toBe(true);
  });

  it("should offer three or more values in a dropdown", () => {
    expect(fixture.debugElement.query(By.directive(MockToggleGroupComponent))).toBeNull();

    const select = fixture.debugElement.query(By.directive(MatSelect));
    select.componentInstance.open();
    fixture.detectChanges();

    const options = fixture.debugElement.queryAll(By.css("mat-option"));
    expect(options.map((option) => option.componentInstance.value)).toEqual(["val1", "val2", "val3"]);
  });

  it("should offer fewer than three values as a toggle group", () => {
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "switch", value: ["val1", "val2"] });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.directive(MockToggleGroupComponent))).not.toBeNull();
    expect(fixture.debugElement.query(By.directive(MatSelect))).toBeNull();
  });

  it("should pass the values, labels and current value to the toggle group, without the check icon", () => {
    fixture.componentRef.setInput("action", { name: "test_action", value: "val2" });
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "switch", value: ["val1", "val2"] });
    fixture.detectChanges();

    const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent)).componentInstance;

    expect(toggleGroup.values()).toEqual(["val1", "val2"]);
    expect(toggleGroup.value()).toBe("val2");
    expect(toggleGroup.groupLabel()).toBe("test_action");
    expect(toggleGroup.hideSelectionIndicator()).toBe(true);
  });

  it("should emit updateAction when a toggle is selected", () => {
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "switch", value: ["val1", "val2"] });
    fixture.detectChanges();
    const emitSpy = jest.spyOn(component.updateAction, "emit");

    fixture.debugElement.query(By.directive(MockToggleGroupComponent)).componentInstance.value.set("val1");
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith("val1");
  });

  it("should emit updateAction with the option picked in the dropdown", () => {
    const emitSpy = jest.spyOn(component.updateAction, "emit");

    fixture.debugElement.query(By.directive(MatSelect)).componentInstance.open();
    fixture.detectChanges();
    fixture.debugElement.queryAll(By.css("mat-option"))[1].nativeElement.click();
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith("val2");
  });

  it("should highlight the search term in the action name", () => {
    fixture.componentRef.setInput("highlight", "action");
    fixture.detectChanges();

    const label = fixture.debugElement.query(By.css(".detail-label")).nativeElement as HTMLElement;
    expect(label.querySelector(".highlight")?.textContent).toBe("action");
  });

  it("should name the value controls after the action", () => {
    const select = fixture.debugElement.query(By.directive(MatSelect)).nativeElement as HTMLElement;
    expect(select.getAttribute("aria-label")).toBe("test_action");

    for (const type of ["str", "int", "text"] as const) {
      fixture.componentRef.setInput("actionDetail", { type, desc: "" });
      fixture.detectChanges();
      const control = fixture.debugElement.query(By.css(".detail-value input, .detail-value textarea"));
      expect(control.nativeElement.getAttribute("aria-label")).toBe("test_action");
    }
  });

  describe("value inputs", () => {
    const setType = (type: "str" | "int" | "text", value: string | number = "") => {
      fixture.componentRef.setInput("action", { name: "test_action", value });
      fixture.componentRef.setInput("actionDetail", { type, desc: "" });
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

    it("shows the current value in the control", async () => {
      setType("str", "shown");
      await fixture.whenStable();
      fixture.detectChanges();

      expect(control("input").value).toBe("shown");
    });

    it("does not emit when it is created or its action is replaced", async () => {
      const spy = jest.spyOn(component.updateAction, "emit");

      setType("str", "first");
      await fixture.whenStable();
      setType("int", 7);
      await fixture.whenStable();
      fixture.detectChanges();

      expect(spy).not.toHaveBeenCalled();
    });

    it("emits the typed string", async () => {
      setType("str");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "typed");

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("typed");
    });

    it("emits the typed number as text", async () => {
      setType("int");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "42");

      expect(spy).toHaveBeenCalledWith("42");
    });

    it("does not emit an emptied number, which is neither an empty value nor 0", async () => {
      setType("int", "5");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "");

      expect(spy).not.toHaveBeenCalled();
      expect(component.valueModel()).toBe("");
      expect(component.valueForm().valid()).toBe(false);
      expect(component.valid()).toBe(false);
    });

    it("emits the number typed after an emptied one", async () => {
      setType("int", "5");
      await type(control("input"), "");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "7");

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("7");
      expect(component.valid()).toBe(true);
    });

    it("does not emit when the emptied number is typed back to the action's value", async () => {
      setType("int", "5");
      await type(control("input"), "");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "5");

      expect(spy).not.toHaveBeenCalled();
      expect(component.valid()).toBe(true);
    });

    it("does not emit a blanked string or text", async () => {
      setType("str", "x");
      const spy = jest.spyOn(component.updateAction, "emit");
      await type(control("input"), "  ");
      setType("text", "y");
      await type(control("textarea"), "");

      expect(spy).not.toHaveBeenCalled();
      expect(component.valid()).toBe(false);
    });

    it("does not emit a number with a fraction", async () => {
      setType("int", "5");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "5.5");

      expect(spy).not.toHaveBeenCalled();
      expect(component.valid()).toBe(false);
    });

    it("does not emit a selection that clears a multi select", () => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "val1" });
      fixture.componentRef.setInput("actionDetail", { type: "str", desc: "", value: ["val1", "val2"], multiple: true });
      fixture.detectChanges();
      const spy = jest.spyOn(component.updateAction, "emit");

      component.updateValue([]);
      fixture.detectChanges();

      expect(spy).not.toHaveBeenCalled();
      expect(component.valid()).toBe(false);
    });

    it("does not emit again when the parent hands the emitted value back", async () => {
      setType("str", "a");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "b");
      fixture.componentRef.setInput("action", { name: "test_action", value: "b" });
      fixture.detectChanges();
      await fixture.whenStable();

      expect(spy).toHaveBeenCalledTimes(1);
      expect(control("input").value).toBe("b");
    });

    it("does not emit when the user types the value the action already has", async () => {
      setType("str", "a");
      await type(control("input"), "b");
      fixture.componentRef.setInput("action", { name: "test_action", value: "b" });
      fixture.detectChanges();
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("input"), "b");

      expect(spy).not.toHaveBeenCalled();
    });

    it("shows the new value when the action's value changes from outside", async () => {
      setType("str", "a");
      await type(control("input"), "typed");
      const spy = jest.spyOn(component.updateAction, "emit");

      fixture.componentRef.setInput("action", { name: "test_action", value: "from outside" });
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();

      expect(control("input").value).toBe("from outside");
      expect(spy).not.toHaveBeenCalled();
    });

    it("emits the typed text", async () => {
      setType("text");
      const spy = jest.spyOn(component.updateAction, "emit");

      await type(control("textarea"), "line one\nline two");

      expect(spy).toHaveBeenCalledWith("line one\nline two");
    });

    it("shows a numeric action value as text in the number input", async () => {
      setType("int", 7);
      await fixture.whenStable();
      fixture.detectChanges();

      expect(component.valueModel()).toBe("7");
      expect(control("input").value).toBe("7");
    });

    it("keeps the model and reports a parse error while the number input holds text the browser cannot parse", async () => {
      setType("int", "5");
      const spy = jest.spyOn(component.updateAction, "emit");
      const element = control("input") as HTMLInputElement;
      Object.defineProperty(element, "validity", { value: { badInput: true }, configurable: true });

      await type(element, "");

      expect(component.valueModel()).toBe("5");
      expect(
        component
          .valueForm()
          .errors()
          .map((error) => error.kind)
      ).toContain("parse");
      expect(spy).not.toHaveBeenCalled();
      expect(component.valid()).toBe(false);
    });

    it("marks a blank string as invalid with the invalidValue kind", async () => {
      setType("str", "x");

      await type(control("input"), "  ");

      expect(
        component
          .valueForm()
          .errors()
          .map((error) => error.kind)
      ).toEqual([INVALID_ACTION_VALUE]);
    });
  });

  describe("invalid indication", () => {
    const row = (): HTMLElement => fixture.nativeElement.querySelector(".policy-action-item");
    const hint = (): HTMLElement | null => fixture.nativeElement.querySelector(".detail-error");
    const input = (): HTMLInputElement => fixture.nativeElement.querySelector(".detail-value input");
    const typeValue = async (value: string) => {
      input().value = value;
      input().dispatchEvent(new Event("input"));
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };

    beforeEach(() => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "5" });
      fixture.componentRef.setInput("actionDetail", { type: "int", desc: "" });
      fixture.detectChanges();
    });

    it("shows no hint and no error styling while the value is valid", () => {
      expect(hint()).toBeNull();
      expect(row().classList).not.toContain("invalid");
      expect(input().getAttribute("aria-invalid")).toBe("false");
      expect(input().hasAttribute("aria-describedby")).toBe(false);
      expect(component.errorHint()).toBeNull();
    });

    it("asks for a whole number when an emptied number input is invalid", async () => {
      await typeValue("");

      expect(row().classList).toContain("invalid");
      expect(hint()?.textContent).toBe("Enter a whole number.");
      expect(hint()?.getAttribute("role")).toBe("alert");
      expect(input().getAttribute("aria-invalid")).toBe("true");
      expect(input().getAttribute("aria-describedby")).toBe(hint()?.id);
    });

    it("asks for a whole number when the number input holds text the browser cannot parse", async () => {
      Object.defineProperty(input(), "validity", { value: { badInput: true }, configurable: true });

      await typeValue("");

      expect(hint()?.textContent).toBe("Enter a whole number.");
      expect(component.valid()).toBe(false);
    });

    it("asks for a value when a blank string is invalid", async () => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "x" });
      fixture.componentRef.setInput("actionDetail", { type: "str", desc: "" });
      fixture.detectChanges();

      await typeValue(" ");

      expect(hint()?.textContent).toBe("Enter a value.");
      expect(input().getAttribute("aria-invalid")).toBe("true");
    });

    it("removes the hint once the value is corrected", async () => {
      await typeValue("");
      await typeValue("8");

      expect(hint()).toBeNull();
      expect(row().classList).not.toContain("invalid");
    });

    it("does not count a row without an action detail, which has no control to correct", () => {
      fixture.componentRef.setInput("actionDetail", null);
      fixture.detectChanges();

      expect(component.valueForm().valid()).toBe(false);
      expect(component.valid()).toBe(true);
      expect(hint()).toBeNull();
    });
  });

  describe("valueForm", () => {
    it("is valid for a filled string", () => {
      fixture.componentRef.setInput("actionDetail", { type: "str", desc: "" });
      fixture.detectChanges();

      expect(component.valueForm().valid()).toBe(true);
    });

    it("is invalid without an action detail", () => {
      fixture.componentRef.setInput("actionDetail", null);
      fixture.detectChanges();

      expect(component.valueForm().valid()).toBe(false);
    });

    it("asks the policy service about the detail and the value", () => {
      const policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;

      expect(component.valueForm().valid()).toBe(true);

      expect(policyService.actionValueIsValid).toHaveBeenCalledWith(defaultDetail, "test_value");
    });
  });

  describe("selectedValue", () => {
    it("selects the numeric option matching a stored string value in the toggle group", () => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "6" });
      fixture.componentRef.setInput("actionDetail", { type: "int", desc: "numbers", value: [6, 8] });
      fixture.detectChanges();

      const toggleGroup = fixture.debugElement.query(By.directive(MockToggleGroupComponent));
      expect(toggleGroup.componentInstance.value()).toBe(6);
    });

    it("selects the string option for a numeric-looking stored string in the dropdown", () => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "2" });
      fixture.componentRef.setInput("actionDetail", { type: "str", desc: "", value: ["1", "2", "3"] });
      fixture.detectChanges();

      expect(fixture.debugElement.query(By.directive(MatSelect)).componentInstance.value).toBe("2");
    });

    it("selects the numeric option matching a stored string value in the dropdown", () => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "8" });
      fixture.componentRef.setInput("actionDetail", { type: "int", desc: "", value: [6, 8, 10] });
      fixture.detectChanges();

      expect(fixture.debugElement.query(By.directive(MatSelect)).componentInstance.value).toBe(8);
    });

    it("keeps a value that matches no option", () => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "other" });
      fixture.detectChanges();

      expect(component.selectedValue()).toBe("other");
    });

    it("keeps the value while there are no options", () => {
      fixture.componentRef.setInput("action", { name: "test_action", value: "x" });
      fixture.componentRef.setInput("actionDetail", null);
      fixture.detectChanges();

      expect(component.selectedValue()).toBe("x");
    });
  });

  describe("updateValue", () => {
    it("emits a value written by the select, the multi select or the toggle group", () => {
      const spy = jest.spyOn(component.updateAction, "emit");

      component.updateValue("new_value");
      fixture.detectChanges();

      expect(spy).toHaveBeenCalledWith("new_value");
    });

    it("joins a list of values with spaces", () => {
      const spy = jest.spyOn(component.updateAction, "emit");

      component.updateValue(["a", "b", "c"]);
      fixture.detectChanges();

      expect(spy).toHaveBeenCalledWith("a b c");
    });

    it("writes an empty value when nothing is chosen, which is invalid and so not emitted", () => {
      const spy = jest.spyOn(component.updateAction, "emit");

      component.updateValue(undefined);
      fixture.detectChanges();

      expect(component.valueModel()).toBe("");
      expect(component.valid()).toBe(false);
      expect(spy).not.toHaveBeenCalled();
    });

    it("shows the written value as the selection before the parent hands it back", () => {
      component.updateValue("val2");

      expect(component.selectedValue()).toBe("val2");
      expect(component.selectedItems()).toEqual(["val2"]);
    });
  });

  it("should emit onRemoveAction when delete button is clicked", () => {
    const spy = jest.spyOn(component.removeAction, "emit");
    const deleteBtn = fixture.debugElement.query(By.css(".delete-icon-button"));
    deleteBtn.nativeElement.click();
    expect(spy).toHaveBeenCalled();
  });
});

describe("PolicyActionItemEditComponent with the toggle group", () => {
  let component: PolicyActionItemEditComponent;
  let fixture: ComponentFixture<PolicyActionItemEditComponent>;

  const radios = (): HTMLButtonElement[] =>
    Array.from(fixture.nativeElement.querySelectorAll("app-toggle-group [role=radio]"));
  const checked = (): string[] =>
    radios()
      .filter((radio) => radio.getAttribute("aria-checked") === "true")
      .map((radio) => radio.textContent!.trim());

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyActionItemEditComponent],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyActionItemEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("action", { name: "test_action", value: "val1" });
    fixture.componentRef.setInput("actionDetail", { type: "str", desc: "switch", value: ["val1", "val2"] });
    fixture.detectChanges();
  });

  it("should render the toggles without the check icon and mark the current value", () => {
    expect(radios()).toHaveLength(2);
    expect(checked()).toEqual(["val1"]);
    expect(fixture.nativeElement.querySelector(".mat-pseudo-checkbox")).toBeNull();
  });

  it("should emit updateAction when a toggle is clicked", () => {
    const emitSpy = jest.spyOn(component.updateAction, "emit");

    radios()[1].click();
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith("val2");
  });

  it("should emit updateAction when an arrow key selects the next toggle", () => {
    const emitSpy = jest.spyOn(component.updateAction, "emit");

    radios()[0].dispatchEvent(new KeyboardEvent("keydown", { keyCode: 39, bubbles: true, cancelable: true }));
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith("val2");
  });

  it("should select the numeric option for a stored string value and emit the option as a number", () => {
    fixture.componentRef.setInput("action", { name: "test_action", value: "6" });
    fixture.componentRef.setInput("actionDetail", { type: "int", desc: "switch", value: [6, 8] });
    fixture.detectChanges();
    const emitSpy = jest.spyOn(component.updateAction, "emit");

    expect(checked()).toEqual(["6"]);
    radios()[1].click();
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith(8);
  });

  it("should select a numeric value and emit it as a number", () => {
    fixture.componentRef.setInput("action", { name: "test_action", value: 2 });
    fixture.componentRef.setInput("actionDetail", { type: "int", desc: "switch", value: [1, 2] });
    fixture.detectChanges();
    const emitSpy = jest.spyOn(component.updateAction, "emit");

    expect(checked()).toEqual(["2"]);
    radios()[0].click();
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith(1);
  });
});

@Component({
  standalone: true,
  imports: [PolicyActionItemEditComponent],
  template: `<app-policy-action-item-edit
    [action]="action()"
    [actionDetail]="detail()"
    (updateAction)="onUpdate($event)" />`
})
class HostComponent {
  readonly detail = signal<PolicyActionDetail>({ type: "str", desc: "d" });
  readonly action = signal<{ name: string; value: string | number | boolean }>({ name: "test_action", value: "a" });
  readonly updates: unknown[] = [];

  // Hands the value back the way the actions list does: numbers are stored as text.
  onUpdate(value: string | number | boolean | undefined): void {
    this.updates.push(value);
    this.action.set({ name: "test_action", value: typeof value === "number" ? String(value) : (value ?? "") });
  }
}

describe("PolicyActionItemEditComponent with a parent that hands the value back", () => {
  let host: HostComponent;
  let fixture: ComponentFixture<HostComponent>;

  const settle = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const type = async (element: HTMLInputElement, value: string) => {
    element.value = value;
    element.dispatchEvent(new Event("input"));
    await settle();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    await settle();
  });

  it("emits every change once, including a change back to the value the action started with", async () => {
    const input = fixture.nativeElement.querySelector("input") as HTMLInputElement;

    await type(input, "b");
    await type(input, "a");

    expect(host.updates).toEqual(["b", "a"]);
    expect(host.action().value).toBe("a");
  });

  it("stores a typed number as text and shows it", async () => {
    host.detail.set({ type: "int", desc: "d" });
    host.action.set({ name: "test_action", value: 3 });
    await settle();
    const input = fixture.nativeElement.querySelector("input") as HTMLInputElement;

    expect(input.value).toBe("3");
    await type(input, "12");

    expect(host.updates).toEqual(["12"]);
    expect(host.action().value).toBe("12");
  });
});
