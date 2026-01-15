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

import { EventConditionDetailsComponent } from "./event-condition-details.component";
import { EventService } from "../../../../../../services/event/event.service";
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MockEventService } from "../../../../../../../testing/mock-services/mock-event-service";

describe("EventConditionDetailsComponent", () => {
  let component: EventConditionDetailsComponent;
  let fixture: ComponentFixture<EventConditionDetailsComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventConditionDetailsComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventConditionDetailsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("conditionName", "");
    fixture.componentRef.setInput("originalConditionValue", null);
    fixture.componentRef.setInput("isEditMode", false);
    fixture.componentRef.setInput("isNewCondition", false);
    component.conditionSubmitted = { emit: jest.fn() } as any;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should compute conditionDetails from service", () => {
    // empty condition name
    fixture.componentRef.setInput("conditionName", "");
    fixture.detectChanges();
    expect(component.conditionDetails()).toEqual({});

    // existing condition name
    fixture.componentRef.setInput("conditionName", "condA");
    fixture.detectChanges();
    expect(component.conditionDetails()).toEqual({ type: "bool", desc: "descA" });
  });

  it("conditionValue should be a list", () => {
    fixture.componentRef.setInput("conditionName", "condD");
    fixture.componentRef.setInput("originalConditionValue", "value1,value2");
    fixture.detectChanges();
    expect(component.conditionValue()).toEqual(["value1", "value2"]);
  });

  it("conditionValue should be a string", () => {
    fixture.componentRef.setInput("conditionName", "condB");
    fixture.componentRef.setInput("originalConditionValue", "value1");
    fixture.detectChanges();
    expect(component.conditionValue()).toEqual("value1");
  });

  it("conditionValue should preselect the first value of a single select", () => {
    fixture.componentRef.setInput("conditionName", "condC");
    fixture.componentRef.setInput("originalConditionValue", null);
    fixture.detectChanges();
    expect(component.conditionValue()).toEqual(1);
  });

  it("should split multi value into array", () => {
    mockEventService.moduleConditions = jest.fn(() => ({
      multiCond: {
        type: "multi",
        value: [{ name: "a" }, { name: "b" }]
      }
    })) as any;
    fixture.componentRef.setInput("conditionName", "multiCond");
    fixture.componentRef.setInput("originalConditionValue", "a,b");
    fixture.detectChanges();
    expect(component.conditionValue()).toEqual(["a", "b"]);
  });

  it("should use default value from details if no originalConditionValue", () => {
    mockEventService.moduleConditions = jest.fn(() => ({ condC: { type: "str", value: ["foo", "bar"] } })) as any;
    fixture.componentRef.setInput("conditionName", "condC");
    fixture.componentRef.setInput("originalConditionValue", null);
    fixture.detectChanges();
    expect(component.conditionValue()).toBe("foo");
  });

  it("should return availableConditionValues for multi type", () => {
    mockEventService.moduleConditions = jest.fn(() => ({
      multiCond: {
        type: "multi",
        value: [{ name: "a" }, { name: "b" }]
      }
    })) as any;
    fixture.componentRef.setInput("conditionName", "multiCond");
    fixture.detectChanges();
    expect(component.availableConditionValues()).toEqual(["a", "b"]);
  });

  it("should return availableConditionValues for non-multi type", () => {
    mockEventService.moduleConditions = jest.fn(() => ({ condC: { type: "str", value: ["foo", "bar"] } })) as any;
    fixture.componentRef.setInput("conditionName", "condC");
    fixture.detectChanges();
    expect(component.availableConditionValues()).toEqual(["foo", "bar"]);
  });

  it("should emit joined value for multi on submit", () => {
    mockEventService.moduleConditions = jest.fn(() => ({
      multiCond: {
        type: "multi",
        value: [{ name: "a" }, { name: "b" }]
      }
    })) as any;
    fixture.componentRef.setInput("conditionName", "multiCond");
    fixture.componentRef.setInput("originalConditionValue", "a,b");
    fixture.detectChanges();
    component.submitCondition();
    expect(component.conditionSubmitted.emit).toHaveBeenCalledWith("a,b");
  });

  it("should emit value for non-multi on submit", () => {
    fixture.componentRef.setInput("conditionName", "condA");
    fixture.componentRef.setInput("originalConditionValue", "true");
    fixture.detectChanges();
    component.submitCondition();
    expect(component.conditionSubmitted.emit).toHaveBeenCalledWith("true");
  });

  it("should validate input for bool type", () => {
    mockEventService.moduleConditions = jest.fn(() => ({ condA: { type: "bool" } })) as any;
    fixture.componentRef.setInput("conditionName", "condA");
    fixture.detectChanges();
    expect(component.inputIsValid()).toBe(true);
  });

  it("should validate input for non-bool type", () => {
    mockEventService.moduleConditions = jest.fn(() => ({ condC: { type: "str" } })) as any;
    fixture.componentRef.setInput("conditionName", "condC");
    fixture.componentRef.setInput("originalConditionValue", "foo");
    fixture.detectChanges();
    expect(component.inputIsValid()).toBe(true);
    fixture.componentRef.setInput("originalConditionValue", "");
    fixture.detectChanges();
    expect(component.inputIsValid()).toBe(false);
  });
});
