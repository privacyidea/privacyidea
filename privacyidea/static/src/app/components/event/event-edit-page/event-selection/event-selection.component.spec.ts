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
import { EventService } from "@services/event/event.service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { EventSelectionComponent } from "./event-selection.component";

describe("EventsSelectionComponent", () => {
  let component: EventSelectionComponent;
  let fixture: ComponentFixture<EventSelectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventSelectionComponent],
      providers: [provideHttpClient(), { provide: EventService, useClass: MockEventService }]
    }).compileComponents();

    fixture = TestBed.createComponent(EventSelectionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("events", ["eventA", "eventB"]);
    jest.spyOn(component.newEvents, "emit");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize editEvents from input", () => {
    fixture.componentRef.setInput("events", ["foo", "bar"]);
    fixture.detectChanges();
    expect(component.selectedEvents()).toEqual(["foo", "bar"]);
  });

  it("should remove an event", () => {
    component.selectedEvents.set(["eventA", "eventB", "eventC"]);
    component.removeEvent("eventB");
    expect(component.selectedEvents()).toEqual(["eventA", "eventC"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventA", "eventC"]);
  });

  it("remove a non existing event should do nothing", () => {
    component.selectedEvents.set(["eventA", "eventB", "eventC"]);
    component.removeEvent("invalid");
    expect(component.selectedEvents()).toEqual(["eventA", "eventB", "eventC"]);
    expect(component.newEvents.emit).not.toHaveBeenCalled();
  });

  it("should add an event", () => {
    component.selectedEvents.set(["eventA"]);
    component.addEvent("eventC");
    expect(component.selectedEvents()).toEqual(["eventA", "eventC"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventA", "eventC"]);
  });

  it("should return all available events if none selected and no search", () => {
    component.selectedEvents.set([]);
    component.searchModel.set({ search: "" });
    const result = component.remainingEvents();
    expect(result).toEqual(["eventA", "eventAB", "eventB", "eventC"]);
  });

  it("remainingEvents should filter out selected events", () => {
    component.selectedEvents.set(["eventA"]);
    component.searchModel.set({ search: "" });
    const result = component.remainingEvents();
    expect(result).toEqual(["eventAB", "eventB", "eventC"]);
  });

  it("remainingEvents should filter by search term (case-insensitive)", () => {
    component.selectedEvents.set([]);
    component.searchModel.set({ search: "eventb" });
    const result = component.remainingEvents();
    expect(result).toEqual(["eventB"]);
  });

  it("remainingEvents should filter by search term (case-insensitive) and filter out selected events", () => {
    component.selectedEvents.set(["eventA"]);
    component.searchModel.set({ search: "entA" });
    const result = component.remainingEvents();
    expect(result).toEqual(["eventAB"]);
  });

  it("remainingEvents should return empty if all events are selected", () => {
    component.selectedEvents.set(["eventA", "eventAB", "eventB", "eventC"]);
    component.searchModel.set({ search: "" });
    const result = component.remainingEvents();
    expect(result).toEqual([]);
  });

  it("should remove an event and emit the updated list", () => {
    component.selectedEvents.set(["eventA", "eventB"]);
    component.removeEvent("eventA");
    expect(component.selectedEvents()).toEqual(["eventB"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventB"]);
  });

  describe("search box", () => {
    const searchInput = (): HTMLInputElement => fixture.nativeElement.querySelector("input.search-input");
    const eventNames = (): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll(".event-item .event-name")).map((el) =>
        (el as HTMLElement).textContent!.trim()
      );
    const type = (value: string) => {
      searchInput().value = value;
      searchInput().dispatchEvent(new Event("input"));
      fixture.detectChanges();
    };

    it("should write the typed text to the search model", () => {
      type("eventb");
      expect(component.searchModel()).toEqual({ search: "eventb" });
      expect(component.searchTerm()).toBe("eventb");
      expect(component.searchForm.search().dirty()).toBe(true);
    });

    it("should filter the offered events while typing", () => {
      component.selectedEvents.set([]);
      type("eventb");
      expect(eventNames()).toEqual(["eventB"]);
    });

    it("should show the typed text in the input when the model changes", () => {
      component.searchModel.set({ search: "entA" });
      fixture.detectChanges();
      expect(searchInput().value).toBe("entA");
    });

    it("should only show the clear button while the search is not empty", () => {
      expect(fixture.nativeElement.querySelector("app-clear-button")).toBeNull();
      type("a");
      expect(fixture.nativeElement.querySelector("app-clear-button")).not.toBeNull();
    });

    it("should clear the search and the input", () => {
      type("eventb");
      component.clearSearch();
      fixture.detectChanges();
      expect(component.searchTerm()).toBe("");
      expect(searchInput().value).toBe("");
    });

    it("should clear the search when the clear button is clicked", () => {
      type("eventb");
      fixture.nativeElement.querySelector("app-clear-button button").click();
      fixture.detectChanges();
      expect(component.searchTerm()).toBe("");
      expect(searchInput().value).toBe("");
    });
  });
});
