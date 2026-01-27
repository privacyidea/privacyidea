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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EventSelectionComponent } from "./event-selection.component";
import { EventService } from "../../../../services/event/event.service";
import { MockEventService } from "../../../../../testing/mock-services/mock-event-service";

describe("EventsSelectionComponent", () => {
  let component: EventSelectionComponent;
  let fixture: ComponentFixture<EventSelectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventSelectionComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventSelectionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("events", ["eventA", "eventB"]);
    fixture.componentRef.setInput("isEditMode", true);
    component.newEvents = { emit: jest.fn() } as any;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize editEvents from input", () => {
    component.selectedEvents.setValue([]);
    fixture.componentRef.setInput("events", ["foo", "bar"]);
    fixture.detectChanges();
    expect(component.selectedEvents.value).toEqual(["foo", "bar"]);
  });

  it("should remove an event", () => {
    component.selectedEvents.setValue(["eventA", "eventB", "eventC"]);
    component.removeEvent("eventB");
    expect(component.selectedEvents.value).toEqual(["eventA", "eventC"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventA", "eventC"]);
  });

  it("remove a non existing event should do nothing", () => {
    component.selectedEvents.setValue(["eventA", "eventB", "eventC"]);
    component.removeEvent("invalid");
    expect(component.selectedEvents.value).toEqual(["eventA", "eventB", "eventC"]);
    expect(component.newEvents.emit).not.toHaveBeenCalled();
  });

  it("should add an event", () => {
    component.selectedEvents.setValue(["eventA"]);
    component.addEvent("eventC");
    expect(component.selectedEvents.value).toEqual(["eventA", "eventC"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventA", "eventC"]);
  });

  it("should return all available events if none selected and no search", () => {
    component.selectedEvents.setValue([]);
    component.searchTerm.set("");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventA", "eventAB", "eventB", "eventC"]);
  });

  it("remainingEvents should filter out selected events", () => {
    component.selectedEvents.setValue(["eventA"]);
    component.searchTerm.set("");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventAB", "eventB", "eventC"]);
  });

  it("remainingEvents should filter by search term (case-insensitive)", () => {
    component.selectedEvents.setValue([]);
    component.searchTerm.set("eventb");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventB"]);
  });

  it("remainingEvents should filter by search term (case-insensitive) and filter out selected events", () => {
    component.selectedEvents.setValue(["eventA"]);
    component.searchTerm.set("entA");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventAB"]);
  });

  it("remainingEvents should return empty if all events are selected", () => {
    component.selectedEvents.setValue(["eventA", "eventAB", "eventB", "eventC"]);
    component.searchTerm.set("");
    const result = component.remainingEvents();
    expect(result).toEqual([]);
  });

  it("should reopen autocomplete panel after selecting an option", () => {
    // Mock the MatAutocompleteTrigger
    component.autocompleteTrigger = {
      openPanel: jest.fn()
    } as any;
    // Simulate selecting an option
    const event = { option: { viewValue: "eventB", deselect: jest.fn() } } as any;
    component.lastSearchTerm = "ev";
    component.selected(event);
    setTimeout(() => {
      // The panel should be reopened
      expect(component.autocompleteTrigger.openPanel).toHaveBeenCalled();
    });
  });

  it("should keep the search term after selecting an option", () => {
    component.searchTerm.set("ev");
    component.lastSearchTerm = "ev";
    const event = { option: { viewValue: "eventB", deselect: jest.fn() } } as any;
    component.selected(event);
    // The search term should remain unchanged
    expect(component.searchTerm()).toBe("ev");
  });

  it("should remove an event and emit the updated list", () => {
    component.selectedEvents.setValue(["eventA", "eventB"]);
    component.removeEvent("eventA");
    expect(component.selectedEvents.value).toEqual(["eventB"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventB"]);
  });

  it("should update searchTerm and lastSearchTerm on input changes", () => {
    const event = { target: { value: "foobar" } };
    component.onSearchInputChanges(event);
    expect(component.lastSearchTerm).toBe("foobar");
    expect(component.searchTerm()).toBe("foobar");
  });

  it("should handle empty string in onSearchInputChanges", () => {
    const event = { target: { value: "" } };
    component.onSearchInputChanges(event);
    expect(component.lastSearchTerm).toBe("");
    expect(component.searchTerm()).toBe("");
  });

  it("should clear search term and lastSearchTerm", () => {
    component.searchTerm.set("something");
    component.lastSearchTerm = "something";
    component.clearSearchTerm();
    expect(component.searchTerm()).toBe("");
    expect(component.lastSearchTerm).toBe("");
  });
});
