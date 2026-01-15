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

import { EventsTabComponent } from "./events-tab.component";
import { EventService } from "../../../../../services/event/event.service";
import { MockEventService } from "../../../../../../testing/mock-services/mock-event-service";
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";

describe("EventsTabComponent", () => {
  let component: EventsTabComponent;
  let fixture: ComponentFixture<EventsTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventsTabComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventsTabComponent);
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
    component.editEvents.set([]);
    fixture.componentRef.setInput("events", ["foo", "bar"]);
    fixture.detectChanges();
    expect(component.editEvents()).toEqual(["foo", "bar"]);
  });

  it("should remove an event", () => {
    component.editEvents.set(["eventA", "eventB", "eventC"]);
    component.removeEvent("eventB");
    expect(component.editEvents()).toEqual(["eventA", "eventC"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventA", "eventC"]);
  });

  it("remove a non existing event should do nothing", () => {
    component.editEvents.set(["eventA", "eventB", "eventC"]);
    component.removeEvent("invalid");
    expect(component.editEvents()).toEqual(["eventA", "eventB", "eventC"]);
    expect(component.newEvents.emit).not.toHaveBeenCalled();
  });

  it("should add an event", () => {
    component.editEvents.set(["eventA"]);
    component.addEvent("eventC");
    expect(component.editEvents()).toEqual(["eventA", "eventC"]);
    expect(component.newEvents.emit).toHaveBeenCalledWith(["eventA", "eventC"]);
  });

  it("should return all available events if none selected and no search", () => {
    component.editEvents.set([]);
    component.searchTerm.set("");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventA", "eventAB", "eventB", "eventC"]);
  });

  it("remainingEvents should filter out selected events", () => {
    component.editEvents.set(["eventA"]);
    component.searchTerm.set("");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventAB", "eventB", "eventC"]);
  });

  it("remainingEvents should filter by search term (case-insensitive)", () => {
    component.editEvents.set([]);
    component.searchTerm.set("eventb");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventB"]);
  });

  it("remainingEvents should filter by search term (case-insensitive) and filter out selected events", () => {
    component.editEvents.set(["eventA"]);
    component.searchTerm.set("entA");
    const result = component.remainingEvents();
    expect(result).toEqual(["eventAB"]);
  });

  it("remainingEvents should return empty if all events are selected", () => {
    component.editEvents.set(["eventA", "eventAB", "eventB", "eventC"]);
    component.searchTerm.set("");
    const result = component.remainingEvents();
    expect(result).toEqual([]);
  });
});
