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

import { ElementRef, OutputEmitterRef, QueryList } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";

import { EventService } from "@services/event/event.service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { EventConditionListComponent } from "./event-condition-list.component";

interface ConditionEvent {
  conditionName: string;
  conditionValue: string | string[];
}

describe("EventConditionListComponent", () => {
  let component: EventConditionListComponent;
  let fixture: ComponentFixture<EventConditionListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventConditionListComponent],
      providers: [{ provide: EventService, useClass: MockEventService }]
    }).compileComponents();

    fixture = TestBed.createComponent(EventConditionListComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("conditions", { condA: "valA", condB: "valB" });
    fixture.componentRef.setInput("action", "add");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize editConditions from input", () => {
    expect(component.editConditions()).toEqual({ condA: "valA", condB: "valB" });
  });

  it("enableShowDescription should set showDescription to true", () => {
    expect(component.showDescription["condA"]).toBeUndefined();
    component.enableShowDescription("condA");
    expect(component.showDescription["condA"]).toBe(true);
    component.showDescription["condA"] = false;
    component.enableShowDescription("condA");
    expect(component.showDescription["condA"]).toBe(true);
  });

  it("disableShowDescription should set showDescription to false", () => {
    expect(component.showDescription["condA"]).toBeUndefined();
    component.disableShowDescription("condA");
    expect(component.showDescription["condA"]).toBe(false);
    component.showDescription["condA"] = true;
    component.disableShowDescription("condA");
    expect(component.showDescription["condA"]).toBe(false);
  });

  it("should get multi values from string and array", () => {
    expect(component.getMultiValues("a,b,c")).toEqual(["a", "b", "c"]);
    expect(component.getMultiValues(["x", "y"])).toEqual(["x", "y"]);
    expect(component.getMultiValues("")).toEqual([]);
  });

  it("should emit newConditionValue on value change if emitOnConditionValueChange is true", () => {
    const emitSpy = jest.fn();
    fixture.componentRef.setInput("emitOnConditionValueChange", true);
    component.newConditionValue = { emit: emitSpy } as unknown as OutputEmitterRef<ConditionEvent>;
    component.onConditionValueChange("condA", "newVal");
    expect(component.editConditions()["condA"]).toBe("newVal");
    expect(emitSpy).toHaveBeenCalledWith({ conditionName: "condA", conditionValue: "newVal" });
  });

  it("should emit multi value conditions as comma separated list", () => {
    const emitSpy = jest.fn();
    fixture.componentRef.setInput("emitOnConditionValueChange", true);
    component.newConditionValue = { emit: emitSpy } as unknown as OutputEmitterRef<ConditionEvent>;
    component.onConditionValueChange("condD", ["option1", "option2"]);
    expect(component.editConditions()["condD"]).toEqual(["option1", "option2"]);
    expect(component.multiValueConditions()["condD"]).toEqual(["option1", "option2"]);
    expect(emitSpy).toHaveBeenCalledWith({ conditionName: "condD", conditionValue: "option1,option2" });
  });

  it("should not emit newConditionValue if emitOnConditionValueChange is false", () => {
    const emitSpy = jest.fn();
    fixture.componentRef.setInput("emitOnConditionValueChange", false);
    component.newConditionValue = { emit: emitSpy } as unknown as OutputEmitterRef<ConditionEvent>;
    component.onConditionValueChange("condB", "anotherVal");
    expect(component.editConditions()["condB"]).toBe("anotherVal");
    expect(emitSpy).not.toHaveBeenCalled();
  });

  it("should emit actionButtonClicked with correct values", () => {
    const emitSpy = jest.fn();
    component.actionButtonClicked = { emit: emitSpy } as unknown as OutputEmitterRef<ConditionEvent>;
    component.editConditions()["condA"] = "testVal";
    component.onActionButtonClicked("condA");
    expect(emitSpy).toHaveBeenCalledWith({ conditionName: "condA", conditionValue: "testVal" });
  });

  it("should compute availableConditionValues correctly", () => {
    const values = component.availableConditionValues();
    expect(values).toEqual({
      condC: ["1", "2", "3"],
      condD: ["option1", "option2"]
    });
  });

  it("should label condition values with yes/no and keep the raw values of result conditions", () => {
    const eventService = TestBed.inject(EventService) as unknown as MockEventService;
    eventService.moduleConditions.set({
      otppin: { type: "str", desc: "descPin", value: ["0", "1"] },
      token_locked: { type: "str", desc: "descLocked", value: ["True", "False"] },
      result_value: { type: "str", desc: "descResult", value: ["True", "False"] },
      tokentype: { type: "multi", desc: "descTypes", value: [{ name: "hotp" }, { name: "totp" }] }
    });
    fixture.componentRef.setInput("conditions", {});
    fixture.detectChanges();

    expect(component.conditionValueOptions()).toEqual({
      otppin: [
        { value: "0", label: "No" },
        { value: "1", label: "Yes" }
      ],
      token_locked: [
        { value: "True", label: "Yes" },
        { value: "False", label: "No" }
      ],
      result_value: [
        { value: "True", label: "True" },
        { value: "False", label: "False" }
      ],
      tokentype: [
        { value: "hotp", label: "HOTP" },
        { value: "totp", label: "TOTP" }
      ]
    });
  });

  it("should emit the raw condition value when a labelled option is picked", () => {
    const eventService = TestBed.inject(EventService) as unknown as MockEventService;
    eventService.moduleConditions.set({
      token_locked: { type: "str", desc: "descLocked", value: ["True", "False"] }
    });
    fixture.componentRef.setInput("conditions", { token_locked: "" });
    fixture.componentRef.setInput("emitOnConditionValueChange", true);
    const emitted: ConditionEvent[] = [];
    component.newConditionValue.subscribe((event) => emitted.push(event));
    fixture.detectChanges();

    const select = fixture.debugElement.query(By.directive(MatSelect));
    select.componentInstance.open();
    fixture.detectChanges();

    const options = fixture.debugElement.queryAll(By.css("mat-option"));
    expect(options.map((option) => [option.componentInstance.value, option.nativeElement.textContent.trim()])).toEqual([
      ["True", "Yes"],
      ["False", "No"]
    ]);

    options[0].nativeElement.click();
    fixture.detectChanges();

    expect(emitted).toEqual([{ conditionName: "token_locked", conditionValue: "True" }]);
    expect(component.editConditions()["token_locked"]).toBe("True");
  });

  it("clearConditionValue should reset the value and emit when emitOnConditionValueChange is true", () => {
    const emitSpy = jest.fn();
    fixture.componentRef.setInput("emitOnConditionValueChange", true);
    component.newConditionValue = { emit: emitSpy } as unknown as OutputEmitterRef<ConditionEvent>;
    component.clearConditionValue("condA");
    expect(component.editConditions()["condA"]).toBe("");
    expect(emitSpy).toHaveBeenCalledWith({ conditionName: "condA", conditionValue: "" });
  });

  it("clearConditionValue should reset the value without emitting when emitOnConditionValueChange is false", () => {
    const emitSpy = jest.fn();
    fixture.componentRef.setInput("emitOnConditionValueChange", false);
    component.newConditionValue = { emit: emitSpy } as unknown as OutputEmitterRef<ConditionEvent>;
    component.clearConditionValue("condB");
    expect(component.editConditions()["condB"]).toBe("");
    expect(emitSpy).not.toHaveBeenCalled();
  });

  it("should focus the matching input when focusConditionName is set", () => {
    jest.useFakeTimers();
    const focusSpy = jest.fn();
    const matchingInput = new ElementRef({ name: "conditionInput_condA", focus: focusSpy });
    const otherInput = new ElementRef({ name: "conditionInput_condB", focus: jest.fn() });
    component.selectedConditionInput = {
      toArray: () => [otherInput, matchingInput]
    } as unknown as QueryList<ElementRef | MatSelect>;

    fixture.componentRef.setInput("focusConditionName", "condA");
    fixture.detectChanges();
    jest.runAllTimers();

    expect(focusSpy).toHaveBeenCalled();
    jest.useRealTimers();
  });
});
