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

import { EventPanelComponent } from "./event-panel.component";
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MockEventService } from "../../../../testing/mock-services/mock-event-service";
import { EMPTY_EVENT, EventHandler, EventService } from "../../../services/event/event.service";
import { MockNotificationService, MockPendingChangesService, MockRouter } from "../../../../testing/mock-services";
import { NotificationService } from "../../../services/notification/notification.service";
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";
import { BehaviorSubject } from "rxjs";
import { PendingChangesService } from "../../../services/pending-changes/pending-changes.service";
import { ROUTE_PATHS } from "../../../route_paths";

global.IntersectionObserver = class IntersectionObserver {
  constructor() {}

  disconnect() {}

  observe() {}

  unobserve() {}

  takeRecords() { return []; }
} as any;

const mockEventHandler: EventHandler = {
  id: "1",
  name: "TestHandler",
  handlermodule: "mockModule",
  active: true,
  event: ["eventA", "eventB"],
  action: "actionB",
  options: { opt3: "true" },
  conditions: { condA: true },
  position: "post",
  ordering: 0
};

describe("EventPanelComponent — edit mode", () => {
  let component: EventPanelComponent;
  let fixture: ComponentFixture<EventPanelComponent>;
  let mockEventService: MockEventService;
  let mockNotificationService: MockNotificationService;
  let mockRouter: MockRouter;
  let mockPendingChangesService: MockPendingChangesService;
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;

  beforeEach(async () => {
    paramMap$ = new BehaviorSubject(convertToParamMap({ id: mockEventHandler.id }));

    await TestBed.configureTestingModule({
      imports: [EventPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: Router, useClass: MockRouter },
        { provide: ActivatedRoute,
          useValue: {
            paramMap: paramMap$.asObservable(),
            snapshot: { paramMap: convertToParamMap({ id: mockEventHandler.id }) }
          }
        }
      ]
    }).compileComponents();

    // Inject services and set up data BEFORE creating the component
    // so the constructor's paramMap subscription finds the handler immediately
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    mockRouter = TestBed.inject(Router) as unknown as MockRouter;
    mockPendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    mockEventService.eventHandlers.set([mockEventHandler]);
    mockEventService.selectedHandlerModule.set(mockEventHandler.handlermodule);

    fixture = TestBed.createComponent(EventPanelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize editEvent from the event handlers list and set selected handler module", () => {
    expect(component.editEvent().id).toBe(mockEventHandler.id);
    expect(component.editEvent().name).toBe("TestHandler");
    expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
  });

  it("should set isNewEvent to false in edit mode", () => {
    expect(component.isNewEvent()).toBe(false);
  });

  it("should show 'Edit Event Handler' as title", () => {
    expect(component.title()).toEqual("Edit Event Handler");
  });

  it("should set new action using setNewAction", () => {
    component.setNewAction("actionC");
    expect(component.editEvent().action).toBe("actionC");
  });

  it("should set new options using setNewOptions", () => {
    const newOptions = { optX: "valX", optY: 42 };
    component.setNewOptions(newOptions);
    expect(component.editEvent().options).toEqual(newOptions);
  });

  it("should set new conditions using setNewConditions", () => {
    const newConditions = { condX: true, condY: false };
    component.setNewConditions(newConditions);
    expect(component.editEvent().conditions).toEqual(newConditions);
  });

  it("should set new events using setNewEvents", () => {
    const newEvents = ["eventZ", "eventW"];
    component.setNewEvents(newEvents);
    expect(component.editEvent().event).toEqual(newEvents);
  });

  it("should update event handler property using updateEventHandler", () => {
    component.updateEventHandler("name", "HandlerUpdated");
    expect(component.editEvent().name).toBe("HandlerUpdated");
    component.updateEventHandler("ordering", 99);
    expect(component.editEvent().ordering).toBe(99);
  });

  it("validConditionsDefinition should be true if no condition is defined", () => {
    component.editEvent.set({ ...component.editEvent(), conditions: {} });
    expect(component.validConditionsDefinition()).toBe(true);
  });

  it("validConditionsDefinition should be true if all conditions have a value defined", () => {
    component.editEvent.set({ ...component.editEvent(), conditions: { cond1: "1", cond2: false } });
    expect(component.validConditionsDefinition()).toBe(true);
  });

  it("validConditionsDefinition should be false if at least one condition has no value", () => {
    component.editEvent.set({ ...component.editEvent(), conditions: { cond1: "1", cond2: null } });
    expect(component.validConditionsDefinition()).toBe(false);
    component.editEvent.set({ ...component.editEvent(), conditions: { cond1: "1", cond2: "" } });
    expect(component.validConditionsDefinition()).toBe(false);
    component.editEvent.set({ ...component.editEvent(), conditions: { cond1: "1", cond2: undefined } });
    expect(component.validConditionsDefinition()).toBe(false);
  });

  it("canSave should be true if all sections are valid", () => {
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.sectionValidity()["conditions"]).toBe(true);
    expect(component.canSave()).toBe(true);
  });

  it("canSave should be false if name is not set", () => {
    component.editEvent.set({ ...component.editEvent(), name: "" });
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(false);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.sectionValidity()["conditions"]).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("canSave should be false if position is not set", () => {
    component.editEvent.set({ ...component.editEvent(), position: "" });
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(false);
    expect(component.sectionValidity()["conditions"]).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("canSave should be false if event is not set", () => {
    component.editEvent.set({ ...component.editEvent(), event: [] });
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(false);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.sectionValidity()["conditions"]).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("canSave should be false if action definition is invalid", () => {
    component.editEvent.set({ ...component.editEvent(), action: "" });
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(false);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.sectionValidity()["conditions"]).toBe(true);
    expect(component.canSave()).toBe(false);

    component.editEvent.set({ ...component.editEvent(), action: "action" });
    component.validOptions.set(false);
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(false);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.sectionValidity()["conditions"]).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("canSave should be false if handler module is not set", () => {
    mockEventService.selectedHandlerModule.set(null);
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(false);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.sectionValidity()["conditions"]).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("canSave should be false if the conditions are invalid", () => {
    component.editEvent.set({ ...component.editEvent(), conditions: { cond1: null } });
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.sectionValidity()["conditions"]).toBe(false);
    expect(component.canSave()).toBe(false);
  });

  it("cancelEdit should navigate back to events list", () => {
    component.cancelEdit();
    expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EVENTS);
  });

  it("should register hasChanges, save and validChanges with PendingChangesService on init", () => {
    expect(mockPendingChangesService.registerHasChanges).toHaveBeenCalled();
    expect(mockPendingChangesService.registerSave).toHaveBeenCalled();
    expect(mockPendingChangesService.registerValidChanges).toHaveBeenCalled();
  });

  it("hasChanges should be false initially and true after a modification", () => {
    expect(component.hasChanges()).toBe(false);
    component.updateEventHandler("name", "Changed");
    expect(component.hasChanges()).toBe(true);
  });

  it("should save event, reload events and navigate back", () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    const snackBarSpy = jest.spyOn(mockNotificationService, "openSnackBar");

    component.saveEvent();

    const convertedParams = {
      id: "1",
      name: "TestHandler",
      handlermodule: "mockModule",
      active: true,
      event: ["eventA", "eventB"],
      action: "actionB",
      "option.opt3": "true",
      conditions: { condA: true },
      position: "post",
      ordering: 0
    };
    expect(mockEventService.saveEventHandler).toHaveBeenCalledWith(convertedParams);
    expect(reloadSpy).toHaveBeenCalled();
    expect(snackBarSpy).toHaveBeenCalledWith("Event handler updated successfully.");
    expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EVENTS);
  });

  it("should delete event and reload events", async () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    await component.deleteEvent();
    expect(mockEventService.deleteWithConfirmDialog).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should toggle active and call enable/disable on service", () => {
    component.toggleActive(true);
    expect(mockEventService.enableEvent).toHaveBeenCalledWith(mockEventHandler.id);
    component.toggleActive(false);
    expect(mockEventService.disableEvent).toHaveBeenCalledWith(mockEventHandler.id);
  });
});

describe("EventPanelComponent — create new mode", () => {
  let component: EventPanelComponent;
  let fixture: ComponentFixture<EventPanelComponent>;
  let mockEventService: MockEventService;
  let mockNotificationService: MockNotificationService;
  let mockRouter: MockRouter;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: Router, useClass: MockRouter },
        { provide: ActivatedRoute,
          useValue: {
            paramMap: new BehaviorSubject(convertToParamMap({})).asObservable(),
            snapshot: { paramMap: convertToParamMap({}) }
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventPanelComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    mockRouter = TestBed.inject(Router) as unknown as MockRouter;

    fixture.detectChanges();
  });

  it("should set isNewEvent to true", () => {
    expect(component.isNewEvent()).toBe(true);
  });

  it("should show 'Create New Event Handler' as title", () => {
    expect(component.title()).toContain("Create");
  });

  it("should initialize editEvent to EMPTY_EVENT", () => {
    expect(component.editEvent().name).toBe(EMPTY_EVENT.name);
    expect(component.editEvent().event).toEqual(EMPTY_EVENT.event);
  });

  it("should set selectedHandlerModule to first available module", () => {
    expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
  });

  it("should save new event without id and navigate back", () => {
    mockEventService.selectedHandlerModule.set("mockModule");
    component.setNewAction("actionB");
    component.setNewOptions({ opt3: "true" });
    component.setNewEvents(["eventA", "eventB"]);
    component.setNewConditions({ condA: true });
    component.updateEventHandler("name", "TestHandler");
    component.updateEventHandler("position", "pre");

    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    const snackBarSpy = jest.spyOn(mockNotificationService, "openSnackBar");

    component.saveEvent();

    const convertedParams = {
      name: "TestHandler",
      handlermodule: "mockModule",
      active: true,
      event: ["eventA", "eventB"],
      action: "actionB",
      "option.opt3": "true",
      conditions: { condA: true },
      position: "pre",
      ordering: 0
    };
    expect(mockEventService.saveEventHandler).toHaveBeenCalledWith(convertedParams);
    expect(reloadSpy).toHaveBeenCalled();
    expect(snackBarSpy).toHaveBeenCalledWith("Event handler created successfully.");
    expect(mockRouter.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EVENTS);
  });
});
