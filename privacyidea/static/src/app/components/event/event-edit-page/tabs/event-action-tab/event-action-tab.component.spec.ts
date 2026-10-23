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

import { provideHttpClient } from "@angular/common/http";
import { OutputEmitterRef } from "@angular/core";
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { MatSelect } from "@angular/material/select";
import { AuthService } from "@services/auth/auth.service";
import { EventActions, EventService } from "@services/event/event.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { EventActionOptionValues, EventActionTabComponent } from "./event-action-tab.component";

describe("EventActionTabComponent", () => {
  let component: EventActionTabComponent;
  let fixture: ComponentFixture<EventActionTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventActionTabComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventActionTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("action", "add_token_info");
    fixture.componentRef.setInput("options", { key: "test_key", value: "test_value" });
    component.newAction = { emit: jest.fn() } as unknown as OutputEmitterRef<string>;
    component.newOptions = { emit: jest.fn() } as unknown as OutputEmitterRef<EventActionOptionValues>;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize selectedAction from input", () => {
    expect(component.selectedAction()).toBe("add_token_info");
  });

  it("should reset options on action selection change and emit changes", () => {
    component.selectedAction.set("actionB");
    fixture.detectChanges();
    expect(Object.keys(component.selectedOptions())).toEqual(["opt3"]);
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt3: "" });
  });

  it("should update selectedOptions and emit on option change", () => {
    component.selectedOptions.set({ key: "another_key", value: "" });
    fixture.detectChanges();

    expect(component.selectedOptions()).toEqual({ key: "another_key", value: "" });
    expect(component.newOptions.emit).toHaveBeenCalledWith({ key: "another_key", value: "" });
  });

  it("should also emit empty options", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    expect(Object.keys(component.selectedOptions())).toEqual(["opt1", "opt2", "opt3"]);
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt1: "", opt2: "", opt3: "" });

    component.selectedOptions.update((current) => ({ ...current, opt3: "newValue" }));
    fixture.detectChanges();
    expect(component.selectedOptions()).toEqual({ opt1: "", opt2: "", opt3: "newValue" });
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt1: "", opt2: "", opt3: "newValue" });
  });

  it("onActionSelectionChange should emit selected action", () => {
    component.onActionSelectionChange("actionB");
    expect(component.newAction.emit).toHaveBeenCalledWith("actionB");
    expect(component.selectedAction()).toBe("add_token_info");

    component.onActionSelectionChange("");
    expect(component.newAction.emit).toHaveBeenCalledWith("");
  });

  it("actionOptions() should return empty dict if no action is selected", () => {
    component.selectedAction.set("");
    fixture.componentRef.setInput("action", "");
    fixture.detectChanges();
    const opts = component.actionOptions();
    expect(opts).toMatchObject({});
  });

  it("actionOptions() should return options for selected action", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    const opts = component.actionOptions();
    expect(opts["opt1"].type).toBe("bool");
    expect(opts["opt2"].type).toBe("int");
  });

  it("checkOptionVisibility returns true if no visibleIf", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt1")).toBe(true);
  });

  it("checkOptionVisibility returns true if visibleIf is set and value matches", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true, opt2: "3" });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt3")).toBe(true);
  });

  it("checkOptionVisibility returns false if visibleIf is set and value does not match", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true, opt2: "1" });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt3")).toBe(false);
  });

  it("checkOptionVisibility returns true if visibleIf is set, but not visibleValue and dependent value is set", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt2")).toBe(true);
  });

  describe("action select", () => {
    const actionSelect = () => fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
    const pickAction = async (index: number) => {
      actionSelect().open();
      fixture.detectChanges();
      await fixture.whenStable();
      (document.querySelectorAll("mat-option")[index] as HTMLElement).click();
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };

    afterEach(() => {
      document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
    });

    it("should show the action of the input", () => {
      expect(actionSelect().value).toBe("add_token_info");
      expect(component.selectedActionForm().valid()).toBe(true);
    });

    it("should write the picked action to the model and emit it", async () => {
      await pickAction(0);
      expect(component.selectedAction()).toBe("actionA");
      expect(component.selectedActionForm().dirty()).toBe(true);
      expect(component.newAction.emit).toHaveBeenCalledWith("actionA");
    });

    it("should show the required error once the empty action select is touched", () => {
      fixture.componentRef.setInput("action", "");
      fixture.detectChanges();
      expect(
        component
          .selectedActionForm()
          .errors()
          .map((error) => error.kind)
      ).toEqual(["required"]);
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();

      component.selectedActionForm().markAsTouched();
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain(
        "Selecting an action is required"
      );
    });
  });

  describe("action options", () => {
    const optionActions: EventActions = {
      withOptions: {
        flag: { type: "bool", desc: "a flag", required: true },
        amount: { type: "int", desc: "an amount", required: true },
        label: { type: "str", desc: "a label", required: true },
        note: { type: "text", desc: "a note" },
        mode: { type: "str", desc: "a mode", required: true, value: ["fast", "slow"] },
        extra: { type: "str", desc: "extra", required: true, visibleIf: "flag", visibleValue: "true" }
      }
    };
    let mockEventService: MockEventService;
    const control = (selector: string): HTMLInputElement => fixture.nativeElement.querySelector(selector);
    const type = (selector: string, value: string) => {
      const element = control(selector);
      element.value = value;
      element.dispatchEvent(new Event("input"));
      fixture.detectChanges();
    };
    const kinds = (name: string) =>
      component.optionsForm[name]()
        .errors()
        .map((error) => error.kind);

    beforeEach(() => {
      mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
      mockEventService.moduleActions = signal(optionActions);
      fixture.componentRef.setInput("action", "withOptions");
      fixture.componentRef.setInput("options", { amount: "5", label: "L", mode: "fast" });
      fixture.detectChanges();
    });

    it("should create a field for every option of the action and ignore options the action does not define", () => {
      fixture.componentRef.setInput("options", { amount: "5", stale: "x" });
      fixture.detectChanges();
      expect(Object.keys(component.selectedOptions())).toEqual(["flag", "amount", "label", "note", "mode", "extra"]);
      expect(component.optionNames()).toEqual(["flag", "amount", "label", "note", "mode", "extra"]);
    });

    it("should report a required option without value per key", () => {
      expect(kinds("flag")).toEqual(["required"]);
      expect(kinds("amount")).toEqual([]);
      expect(kinds("label")).toEqual([]);
      expect(kinds("note")).toEqual([]);
      expect(component.optionsForm().valid()).toBe(false);
    });

    it("should accept an unchecked required checkbox once it is set to false", () => {
      component.selectedOptions.update((current) => ({ ...current, flag: false }));
      expect(kinds("flag")).toEqual([]);
      expect(component.optionsForm().valid()).toBe(true);
    });

    it("should skip the required rule of an option that is not visible", () => {
      component.selectedOptions.update((current) => ({ ...current, flag: true }));
      expect(component.checkOptionVisibility("extra")).toBe(false);
      expect(kinds("extra")).toEqual([]);
      component.selectedOptions.update((current) => ({ ...current, flag: "true" }));
      expect(component.checkOptionVisibility("extra")).toBe(true);
      expect(kinds("extra")).toEqual(["required"]);
    });

    it("should treat null, undefined and an empty string as empty", () => {
      component.selectedOptions.update((current) => ({ ...current, label: null }));
      expect(kinds("label")).toEqual(["required"]);
      component.selectedOptions.update((current) => ({ ...current, label: "" }));
      expect(kinds("label")).toEqual(["required"]);
      component.selectedOptions.update((current) => ({ ...current, label: "x" }));
      expect(kinds("label")).toEqual([]);
    });

    it("should report no option as invalid before it is touched", () => {
      component.selectedOptions.update((current) => ({ ...current, label: "" }));
      fixture.detectChanges();
      expect(component.showOptionError("label")).toBe(false);
      expect(fixture.nativeElement.querySelector("mat-form-field mat-error")).toBeNull();
    });

    it("should show the required error of an option after its input lost the focus", () => {
      type("input[type=text]", "");
      control("input[type=text]").dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(component.showOptionError("label")).toBe(true);
      expect(fixture.nativeElement.querySelector("mat-form-field mat-error")?.textContent).toContain(
        "label is required"
      );
    });

    it("should hide the description of an option while its error is shown", () => {
      const hints = () => fixture.nativeElement.querySelectorAll(".checkbox-hint").length;
      const before = hints();
      type("input[type=text]", "");
      control("input[type=text]").dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(hints()).toBe(before - 1);
    });

    it("should write typed text of a text input and a textarea to the model and emit the options", () => {
      type("input[type=text]", "typed");
      type("textarea", "multi\nline");
      expect(component.selectedOptions()["label"]).toBe("typed");
      expect(component.selectedOptions()["note"]).toBe("multi\nline");
      expect(component.newOptions.emit).toHaveBeenCalledWith(
        expect.objectContaining({ label: "typed", note: "multi\nline" })
      );
    });

    it("should write a typed number of an int input to the model", () => {
      type("input[type=number]", "42");
      expect(component.selectedOptions()["amount"]).toBe("42");
      expect(kinds("amount")).toEqual([]);
    });

    it("should require a value when an int input is cleared", () => {
      type("input[type=number]", "");
      expect(component.selectedOptions()["amount"]).toBe("");
      expect(kinds("amount")).toEqual(["required"]);
    });

    it("should report a parse error for an unparsable number and block the options", () => {
      const validity = jest.spyOn(control("input[type=number]"), "validity", "get");
      validity.mockReturnValue({ badInput: true } as ValidityState);
      type("input[type=number]", "");
      expect(kinds("amount")).toEqual(["parse"]);
      expect(component.optionsForm().valid()).toBe(false);
      component.optionsForm["amount"]().markAsTouched();
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector("mat-form-field mat-error")?.textContent).toContain(
        "Enter a valid number."
      );
      validity.mockReturnValue({ badInput: false } as ValidityState);
    });

    it("should write the checkbox state to the model", () => {
      fixture.nativeElement.querySelector("mat-checkbox input").click();
      fixture.detectChanges();
      expect(component.selectedOptions()["flag"]).toBe(true);
      expect(component.optionsForm["flag"]().dirty()).toBe(true);
      expect(kinds("flag")).toEqual([]);
    });

    it("should show the model value in the checkbox", () => {
      component.selectedOptions.update((current) => ({ ...current, flag: true }));
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector("mat-checkbox input").checked).toBe(true);
    });

    it("should write the picked value of an option select to the model", async () => {
      const select = fixture.debugElement.queryAll(By.directive(MatSelect))[1].componentInstance as MatSelect;
      expect(select.value).toBe("fast");
      select.open();
      fixture.detectChanges();
      await fixture.whenStable();
      (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
      fixture.detectChanges();
      expect(component.selectedOptions()["mode"]).toBe("slow");
      expect(component.optionsForm["mode"]().dirty()).toBe(true);
      document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
    });

    it("should emit the validity of the options", () => {
      const emitted: boolean[] = [];
      component.optionsValid = {
        emit: (value: boolean) => emitted.push(value)
      } as unknown as typeof component.optionsValid;
      component.selectedOptions.update((current) => ({ ...current, flag: false }));
      fixture.detectChanges();
      expect(emitted.at(-1)).toBe(true);
      component.selectedOptions.update((current) => ({ ...current, label: "" }));
      fixture.detectChanges();
      expect(emitted.at(-1)).toBe(false);
    });

    it("should clear the touched state of the options when they are rebuilt", () => {
      component.optionsForm["label"]().markAsTouched();
      fixture.componentRef.setInput("options", { amount: "7" });
      fixture.detectChanges();
      expect(component.optionsForm["label"]().touched()).toBe(false);
    });

    it("should not offer an option that is not yet part of the model", () => {
      component.selectedOptions.set({});
      expect(component.optionNames()).toEqual([]);
      expect(component.showOptionError("flag")).toBe(false);
    });

    it("should keep the default of an option definition", () => {
      mockEventService.moduleActions = signal({
        withDefault: { opt: { type: "str", default: "preset" } } as unknown as EventActions[string]
      });
      fixture.componentRef.setInput("action", "withDefault");
      fixture.componentRef.setInput("options", {});
      fixture.detectChanges();
      expect(component.selectedOptions()).toEqual({ opt: "preset" });
    });
  });
});
