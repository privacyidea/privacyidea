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

import { ComponentFixture, TestBed } from "@angular/core/testing";

import { EventComponent } from "./event.component";
import { provideHttpClient } from "@angular/common/http";
import { EventHandler, EventService } from "../../services/event/event.service";
import { MockEventService } from "../../../testing/mock-services/mock-event-service";

describe("EventComponent", () => {
  let component: EventComponent;
  let fixture: ComponentFixture<EventComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(EventComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should format conditions as string", () => {
    expect(component.formatConditions({ foo: "bar", baz: 42 })).toBe("foo: bar, baz: 42");
    expect(component.formatConditions({})).toBe("");
    expect(component.formatConditions(null)).toBe("");
    expect(component.formatConditions(undefined)).toBe("");
    expect(component.formatConditions("not-an-object")).toBe("");
  });

  it("should return event array if input is array, else empty array", () => {
    expect(component.getEventArray(["a", "b"])).toEqual(["a", "b"]);
    expect(component.getEventArray("not-an-array")).toEqual([]);
    expect(component.getEventArray(null)).toEqual([]);
    expect(component.getEventArray(undefined)).toEqual([]);
  });

  it("should toggle detailedView", () => {
    const initial = component.detailedView();
    component.toggleDetailedView();
    expect(component.detailedView()).toBe(!initial);
    component.toggleDetailedView();
    expect(component.detailedView()).toBe(initial);
  });

  it("should clear filter and call onFilterInput", () => {
    const spy = jest.spyOn(component, "onFilterInput");
    component.filterString.set("something");
    component.onClearFilter();
    expect(component.filterString()).toBe("");
    expect(spy).toHaveBeenCalledWith("");
  });

  it("should set filterString and update eventHandlerDataSource filter", () => {
    const ds = component.eventHandlerDataSource();
    component.onFilterInput("test");
    expect(component.filterString()).toBe("test");
    expect(ds.filter).toBe("test");
  });

  it("should open dialog for edit event handler", () => {
    const spy = jest.spyOn(component["dialog"], "open");
    const handler = {
      name: "foo",
      event: [],
      handlermodule: "",
      position: "",
      action: "",
      conditions: {},
      options: {},
      active: true,
      ordering: 1
    };
    component.onEditEventHandler(handler as any);
    expect(spy).toHaveBeenCalled();
  });

  it("should open dialog for create new event handler", () => {
    const spy = jest.spyOn(component["dialog"], "open");
    component.onCreateNewEventHandler();
    expect(spy).toHaveBeenCalled();
  });

  it("should call eventService.deleteWithConfirmDialog on delete", () => {
    const spy = jest.spyOn(component["eventService"], "deleteWithConfirmDialog");
    const handler = {
      name: "foo",
      event: [],
      handlermodule: "",
      position: "",
      action: "",
      conditions: {},
      options: {},
      active: true,
      ordering: 1
    };
    component.onDeleteEventHandler(handler as any);
    expect(spy).toHaveBeenCalled();
  });

  it("should filter eventHandlerDataSource by name", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "SpecialName",
      handlermodule: "mod",
      position: "pos",
      action: "act",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "specialname")).toBe(true);
    expect(ds.filterPredicate(handler as any, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by handlermodule", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "n",
      handlermodule: "ModuleX",
      position: "p",
      action: "a",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "modulex")).toBe(true);
    expect(ds.filterPredicate(handler as any, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by position", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "n",
      handlermodule: "m",
      position: "PosY",
      action: "a",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "posy")).toBe(true);
    expect(ds.filterPredicate(handler as any, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by action", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "ActionZ",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "actionz")).toBe(true);
    expect(ds.filterPredicate(handler as any, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by options", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: { foo: "BarOpt" },
      event: [],
      conditions: {},
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "foo: baropt")).toBe(true);
    expect(ds.filterPredicate(handler as any, "foo")).toBe(true);
    expect(ds.filterPredicate(handler as any, "baropt")).toBe(true);
    expect(ds.filterPredicate(handler as any, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by events", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: {},
      event: ["EventA"],
      conditions: {},
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "eventa")).toBe(true);
    expect(ds.filterPredicate(handler as any, "notfound")).toBe(false);
  });

  it("should filter eventHandlerDataSource by conditions", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: {},
      event: [],
      conditions: { cond: "CondVal" },
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "cond: condval")).toBe(true);
    expect(ds.filterPredicate(handler as any, "cond")).toBe(true);
    expect(ds.filterPredicate(handler as any, "condval")).toBe(true);
    expect(ds.filterPredicate(handler as any, "notfound")).toBe(false);
  });

  it("should return true for empty filter in filterPredicate", () => {
    const ds = component.eventHandlerDataSource();
    const handler = {
      name: "n",
      handlermodule: "m",
      position: "p",
      action: "a",
      options: {},
      event: [],
      conditions: {},
      active: true,
      ordering: 1
    };
    expect(ds.filterPredicate(handler as any, "")).toBe(true);
    expect(ds.filterPredicate(handler as any, "   ")).toBe(true);
  });

  it("should update totalLength when eventHandlers changes", () => {
    // Simulate eventHandlers signal update
    const eventHandlers: EventHandler[] = [
      {
        id: "1",
        name: "a",
        event: [],
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        conditions: {},
        active: true,
        ordering: 1
      },
      {
        id: "2",
        name: "b",
        event: [],
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        conditions: {},
        active: true,
        ordering: 2
      }
    ];
    mockEventService.eventHandlers.set(eventHandlers);
    expect(component.totalLength()).toBe(2);
    mockEventService.eventHandlers.set([]);
    expect(component.totalLength()).toBe(0);
  });

  it("should return previous value for totalLength if eventHandlers is null/undefined", () => {
    const eventHandlers: EventHandler[] = [
      {
        id: "1",
        name: "a",
        event: [],
        handlermodule: "",
        position: "",
        action: "",
        options: {},
        conditions: {},
        active: true,
        ordering: 1
      }
    ];
    mockEventService.eventHandlers.set(eventHandlers);
    expect(component.totalLength()).toBe(1);
    mockEventService.eventHandlers.set(undefined);
    expect(component.totalLength()).toBe(1); // stays at previous value
  });

  it('should sort event handlers by name ascending', () => {
    const data = [
      { name: 'Charlie', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 3 },
      { name: 'Alice', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 1 },
      { name: 'Bob', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 2 }
    ];
    const sorted = (component as any).clientsideSortEventData([...data], { active: 'name', direction: 'asc' });
    expect(sorted.map((e: any) => e.name)).toEqual(['Alice', 'Bob', 'Charlie']);
  });

  it('should sort event handlers by name descending', () => {
    const data = [
      { name: 'Charlie', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 3 },
      { name: 'Alice', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 1 },
      { name: 'Bob', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 2 }
    ];
    const sorted = (component as any).clientsideSortEventData([...data], { active: 'name', direction: 'desc' });
    expect(sorted.map((e: any) => e.name)).toEqual(['Charlie', 'Bob', 'Alice']);
  });

  it('should sort event handlers by ordering ascending', () => {
    const data = [
      { name: 'Charlie', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 3 },
      { name: 'Alice', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 1 },
      { name: 'Bob', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 2 }
    ];
    const sorted = (component as any).clientsideSortEventData([...data], { active: 'ordering', direction: 'asc' });
    expect(sorted.map((e: any) => e.ordering)).toEqual([1, 2, 3]);
  });

  it('should sort event handlers by ordering descending', () => {
    const data = [
      { name: 'Charlie', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 3 },
      { name: 'Alice', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 1 },
      { name: 'Bob', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 2 }
    ];
    const sorted = (component as any).clientsideSortEventData([...data], { active: 'ordering', direction: 'desc' });
    expect(sorted.map((e: any) => e.ordering)).toEqual([3, 2, 1]);
  });

  it('should return original array if no direction is set', () => {
    const data = [
      { name: 'Charlie', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 3 },
      { name: 'Alice', handlermodule: '', position: '', action: '', options: {}, event: [], conditions: {}, active: true, ordering: 1 }
    ];
    const sorted = (component as any).clientsideSortEventData([...data], { active: 'name', direction: '' });
    expect(sorted).toEqual(data);
  });

  it('should handle empty array', () => {
    const sorted = (component as any).clientsideSortEventData([], { active: 'name', direction: 'asc' });
    expect(sorted).toEqual([]);
  });

  it('should handle missing sort key gracefully', () => {
    const data = [
      { name: 'Charlie', ordering: 3 },
      { name: 'Alice' },
      { name: 'Bob', ordering: 2 }
    ];
    const sorted = (component as any).clientsideSortEventData([...data], { active: 'ordering', direction: 'asc' });
    expect(sorted.map((e: any) => e.ordering)).toEqual([undefined, 2, 3]);
  });
});
