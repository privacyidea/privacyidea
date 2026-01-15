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

import { EventConditionsTabComponent } from "./event-conditions-tab.component";
import { EventService } from "../../../../../services/event/event.service";
import { MockEventService } from "../../../../../../testing/mock-services/mock-event-service";
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";

describe("EventConditionsTabComponent", () => {
  let component: EventConditionsTabComponent;
  let fixture: ComponentFixture<EventConditionsTabComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventConditionsTabComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventConditionsTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("conditions", { "test_condition": "test_value" });
    fixture.componentRef.setInput("isEditMode", true);
    component.newConditions = { emit: jest.fn() } as any;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize selectedConditions from input", () => {
    component.selectedConditions.set({});
    fixture.componentRef.setInput("conditions", { "foo": "bar" });
    fixture.detectChanges();
    expect(component.selectedConditions()).toEqual({ "foo": "bar" });
  });

  it("should initialize clickedCondition with the first selected condition", () => {
    // No condition available, clickedCondition should be empty
    component.selectedConditions.set({});
    expect(component.clickedCondition()).toBe("");

    // Conditions available, clickedCondition should be that first condition
    component.selectedConditions.set({ "cond1": "val1", "cond2": "val2" });
    expect(component.clickedCondition()).toBe("cond1");
  });

  it("removeCondition", () => {
    component.selectedConditions.set({ "cond1": "val1", "cond2": "val2" });
    component.removeCondition("cond1");
    expect(component.selectedConditions()).toEqual({ "cond2": "val2" });
    expect(component.newConditions.emit).toHaveBeenCalledWith({ "cond2": "val2" });
  });

  it("should emit newConditions on condition submit", () => {
    component.clickedCondition.set("test_condition");
    component.onConditionSubmitted("new_value");
    expect(component.selectedConditions()["test_condition"]).toBe("new_value");
    expect(component.newConditions.emit).toHaveBeenCalledWith(component.selectedConditions());
  });

  it("onConditionSubmitted without a actual condition be clicked should do nothing", () => {
    component.selectedConditions.set({ "cond1": "val1", "cond2": "val2" });
    component.clickedCondition.set("");
    component.onConditionSubmitted("new_value");
    expect(component.selectedConditions()).toEqual({ "cond1": "val1", "cond2": "val2" });
    expect(component.newConditions.emit).not.toHaveBeenCalled();
  });

  it("should return true for boolean condition", () => {
    mockEventService.moduleConditions = jest.fn(() => ({ boolCond: { type: "bool" } })) as any;
    expect(component.isBooleanCondition("boolCond")).toBe(true);
  });

  it("should return false for non-boolean condition", () => {
    mockEventService.moduleConditions = jest.fn(() => ({ strCond: { type: "string" } })) as any;
    expect(component.isBooleanCondition("strCond")).toBe(false);
  });

  it("should return all conditions by group if nothing is selected and no search", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    const result = component.remainingConditionsByGroup();
    expect(result).toEqual({
      group1: {
        condA: { type: "bool", desc: "descA" },
        condB: { type: "str", desc: "descB" }
      },
      group2: {
        condC: { type: "int", desc: "descC" }
      }
    });
  });

  it("should filter out selected conditions", () => {
    component.selectedConditions.set({ condA: "someValue" });
    component.searchTerm.set("");
    const result = component.remainingConditionsByGroup();
    expect(result).toEqual({
      group1: {
        condB: { type: "str", desc: "descB" }
      },
      group2: {
        condC: { type: "int", desc: "descC" }
      }
    });
  });

  it("should filter by search term (case-insensitive)", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("condb");
    const result = component.remainingConditionsByGroup();
    expect(result).toEqual({
      group1: {
        condB: { type: "str", desc: "descB" }
      },
      group2: {}
    });
  });

  it("should return empty groups if all conditions are selected", () => {
    component.selectedConditions.set({ condA: "v", condB: "v", condC: "v" });
    component.searchTerm.set("");
    const result = component.remainingConditionsByGroup();
    expect(result).toEqual({ group1: {}, group2: {} });
  });
});
