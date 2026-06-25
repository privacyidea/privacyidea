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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EventService } from "@services/event/event.service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { EventConditionsTabComponent } from "./event-conditions-tab.component";

describe("EventConditionsTabComponent", () => {
  let component: EventConditionsTabComponent;
  let fixture: ComponentFixture<EventConditionsTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventConditionsTabComponent],
      providers: [provideHttpClient(), { provide: EventService, useClass: MockEventService }]
    }).compileComponents();

    fixture = TestBed.createComponent(EventConditionsTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("conditions", { test_condition: "test_value" });
    component.newConditions = { emit: jest.fn() } as unknown as OutputEmitterRef<Record<string, unknown>>;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize selectedConditions from input", () => {
    component.selectedConditions.set({});
    fixture.componentRef.setInput("conditions", { foo: "bar" });
    fixture.detectChanges();
    expect(component.selectedConditions()).toEqual({ foo: "bar" });
  });

  it("removeCondition", () => {
    component.selectedConditions.set({ cond1: "val1", cond2: "val2" });
    component.removeCondition("cond1");
    expect(component.selectedConditions()).toEqual({ cond2: "val2" });
    expect(component.newConditions.emit).toHaveBeenCalledWith({ cond2: "val2" });
  });

  it("should return all conditions by group if nothing is selected and no search", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    const result = component.remainingConditionsByGroup();
    expect(result).toEqual({
      group1: {
        condA: "",
        condB: ""
      },
      group2: {
        condC: ""
      }
    });
  });

  it("should filter out selected conditions", () => {
    component.selectedConditions.set({ condA: "someValue" });
    component.searchTerm.set("");
    const result = component.remainingConditionsByGroup();
    expect(result).toEqual({
      group1: {
        condB: ""
      },
      group2: {
        condC: ""
      }
    });
  });

  it("should filter by search term (case-insensitive)", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("condb");
    const result = component.remainingConditionsByGroup();
    expect(result).toEqual({
      group1: {
        condB: ""
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

  it("should update conditionsToBeAdded on onConditionValueToBeAddedChange", () => {
    component.conditionsToBeAdded.set({});
    component.onConditionValueToBeAddedChange("condX", "valX");
    expect(component.conditionsToBeAdded()["condX"]).toBe("valX");
  });

  it("should join array values on onConditionValueToBeAddedChange", () => {
    component.conditionsToBeAdded.set({});
    component.onConditionValueToBeAddedChange("condX", ["v1", "v2"]);
    expect(component.conditionsToBeAdded()["condX"]).toBe("v1,v2");
  });

  it("should join array values on onConditionValueChange", () => {
    component.selectedConditions.set({});
    const emitSpy = jest.fn();
    component.newConditions = { emit: emitSpy } as unknown as OutputEmitterRef<Record<string, unknown>>;
    component.onConditionValueChange("condY", ["a", "b"]);
    expect(component.selectedConditions()).toEqual({ condY: "a,b" });
    expect(emitSpy).toHaveBeenCalledWith({ condY: "a,b" });
  });

  it("should update selectedConditions and emit newConditions on onConditionValueChange", () => {
    component.selectedConditions.set({ condY: "oldVal" });
    const emitSpy = jest.fn();
    component.newConditions = { emit: emitSpy } as unknown as OutputEmitterRef<Record<string, unknown>>;
    component.onConditionValueChange("condY", "newVal");
    expect(component.selectedConditions()).toEqual({ condY: "newVal" });
    expect(emitSpy).toHaveBeenCalledWith({ condY: "newVal" });
  });

  it("should set addedCondition when value is empty in onConditionValueChange", () => {
    component.selectedConditions.set({ condZ: "something" });
    component.addedCondition.set("");
    component.newConditions = { emit: jest.fn() } as unknown as OutputEmitterRef<Record<string, unknown>>;
    component.onConditionValueChange("condZ", "");
    expect(component.addedCondition()).toBe("condZ");
  });

  it("availableNonEmptyGroups should only include groups with remaining conditions", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    const groups = component.availableNonEmptyGroups();
    expect(groups).toContain("group1");
    expect(groups).toContain("group2");
  });

  it("availableNonEmptyGroups should exclude groups where all conditions are selected", () => {
    component.selectedConditions.set({ condA: "v", condB: "v" });
    component.searchTerm.set("");
    const groups = component.availableNonEmptyGroups();
    expect(groups).not.toContain("group1");
    expect(groups).toContain("group2");
  });

  it("availableNonEmptyGroups should exclude groups filtered out by search term", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("condC");
    const groups = component.availableNonEmptyGroups();
    expect(groups).not.toContain("group1");
    expect(groups).toContain("group2");
  });

  it("selectedGroup should default to first non-empty group", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    expect(component.selectedGroup()).toBe("group1");
  });

  it("selectedGroup should keep current selection if group is still non-empty", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    component.selectedGroup.set("group2");
    component.selectedConditions.set({ condA: "v" });
    expect(component.selectedGroup()).toBe("group2");
  });

  it("selectedGroup should fall back to empty string when no non-empty groups remain", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    component.selectedGroup.set("group2");
    component.selectedConditions.set({ condA: "v", condB: "v", condC: "v" });
    expect(component.selectedGroup()).toBe("");
  });

  it("remainingConditionsInSelectedGroup should return conditions for the selected group", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    component.selectedGroup.set("group2");
    const result = component.remainingConditionsInSelectedGroup();
    expect(result).toEqual({ condC: "" });
  });

  it("remainingConditionsInSelectedGroup should return empty object for unknown group", () => {
    component.selectedConditions.set({});
    component.searchTerm.set("");
    component.selectedGroup.set("nonExistentGroup");
    const result = component.remainingConditionsInSelectedGroup();
    expect(result).toEqual({});
  });
});
