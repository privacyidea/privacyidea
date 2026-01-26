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
import { EMPTY_EVENT, EventService } from "../../../services/event/event.service";
import { MockNotificationService } from "../../../../testing/mock-services";
import { NotificationService } from "../../../services/notification/notification.service";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";


global.IntersectionObserver = class IntersectionObserver {
  constructor() {}

  disconnect() {}

  observe() {}

  unobserve() {}

  takeRecords() { return []; }
} as any;

describe("EventPanelComponent", () => {
  let component: EventPanelComponent;
  let fixture: ComponentFixture<EventPanelComponent>;
  let mockEventService: MockEventService;
  let mockNotificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService },
        { provide: NotificationService, useClass: MockNotificationService },
        {
          provide: MatDialogRef,
          useValue: {
            close: jest.fn(),
            backdropClick: jest.fn().mockReturnValue(of()),
            keydownEvents: jest.fn().mockReturnValue(of())
          }
        },
        {
          provide: MAT_DIALOG_DATA, useValue: {
            eventHandler: {
              id: 1,
              name: "TestHandler",
              handlermodule: "mockModule",
              active: true,
              event: ["eventA", "eventB"],
              action: "actionB",
              options: { opt3: "true" },
              conditions: { condA: true },
              position: 0
            }
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventPanelComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize event from dialog data and set selected handler module in service", () => {
    expect(component.editEvent().id).toBe(1);
    expect(component.editEvent().name).toBe("TestHandler");
    expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
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

  it("validActionDefinition should be false if no action is defined", () => {
    component.editEvent.set({ ...component.editEvent(), action: "", options: {} });
    expect(component.validActionDefinition()).toBe(false);
  });

  it("validActionDefinition should be false if a required option is not defined", () => {
    // option not set at all
    component.editEvent.set({ ...component.editEvent(), action: "actionA", options: {} });
    expect(component.validActionDefinition()).toBe(false);

    // option value is null
    component.editEvent.set({ ...component.editEvent(), action: "actionA", options: { "opt1": null } });
    expect(component.validActionDefinition()).toBe(false);

    // option value is empty string
    component.editEvent.set({ ...component.editEvent(), action: "actionA", options: { "opt1": "" } });
    expect(component.validActionDefinition()).toBe(false);
  });

  it("validActionDefinition should be true if no action has no required options", () => {
    component.editEvent.set({ ...component.editEvent(), action: "actionB", options: {} });
    expect(component.validActionDefinition()).toBe(true);
  });

  it("validActionDefinition should be true if all required options are defined", () => {
    component.editEvent.set({ ...component.editEvent(), action: "actionA", options: { "opt1": 1 } });
    expect(component.validActionDefinition()).toBe(true);
  });

  it("validConditionsDefinition should be true if no condition is defined", () => {
    component.editEvent.set({ ...component.editEvent(), conditions: {} });
    expect(component.validConditionsDefinition()).toBe(true);
  });

  it("validConditionsDefinition should be true if all conditions have a value defined", () => {
    component.editEvent.set({ ...component.editEvent(), conditions: {cond1: "1", cond2: false} });
    expect(component.validConditionsDefinition()).toBe(true);
  });

  it("validConditionsDefinition should be false if at least one condition has no value", () => {
    component.editEvent.set({ ...component.editEvent(), conditions: {cond1: "1", cond2: null} });
    expect(component.validConditionsDefinition()).toBe(false);
    component.editEvent.set({ ...component.editEvent(), conditions: {cond1: "1", cond2: ""} });
    expect(component.validConditionsDefinition()).toBe(false);
    component.editEvent.set({ ...component.editEvent(), conditions: {cond1: "1", cond2: undefined} });
    expect(component.validConditionsDefinition()).toBe(false);
  });

  it("canSave should be true if all sections are valid", () => {
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
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
    expect(component.canSave()).toBe(false);
  });

  it("canSave should be false if handler module is not set", () => {
    mockEventService.selectedHandlerModule.set(null);
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(true);
    expect(component.sectionValidity()["handlerModule"]).toBe(false);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("should cancel edit", () => {
    // Simulate unsaved changes
    component.editEvent.set({ ...component.editEvent(), name: "Changed" });

    // Mock dialog.open to return an object with afterClosed returning an observable of true (confirmed)
    const afterClosedMock = jest.fn().mockReturnValue(of(true));
    const openMock = jest.spyOn(component["dialog"], "open").mockReturnValue({
      afterClosed: afterClosedMock
    } as any);

    // Call cancelEdit
    component.cancelEdit();

    // The editEvent should be reset to the original event (from this.event())
    expect(component.editEvent().name).toBe(component.event().name);
    expect(openMock).toHaveBeenCalled();
    expect(afterClosedMock).toHaveBeenCalled();
  });


  it("should save event and reload events", () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    const snackBarSpy = jest.spyOn(mockNotificationService, "openSnackBar");
    // ensure effect is triggered to set the selected handler module in the service
    fixture.detectChanges();

    // act
    component.saveEvent();

    // id converted to string and converted options in ugly format
    const convertedParams = {
      id: "1",
      name: "TestHandler",
      handlermodule: "mockModule",
      active: true,
      event: ["eventA", "eventB"],
      action: "actionB",
      "option.opt3": "true",
      conditions: { condA: true },
      position: 0
    };
    expect(mockEventService.saveEventHandler).toHaveBeenCalledWith(convertedParams);
    expect(reloadSpy).toHaveBeenCalled();
    expect(snackBarSpy).toHaveBeenCalledWith("Event handler updated successfully.");
  });

  it("should delete event and reload events", () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    component.deleteEvent();
    expect(mockEventService.deleteWithConfirmDialog).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should toggle active and call enable/disable on service", () => {
    component.toggleActive(true);
    expect(mockEventService.enableEvent).toHaveBeenCalledWith(1);
    component.toggleActive(false);
    expect(mockEventService.disableEvent).toHaveBeenCalledWith(1);
  });
});

describe("CreateNewEventHandler", () => {
  let component: EventPanelComponent;
  let fixture: ComponentFixture<EventPanelComponent>;
  let mockEventService: MockEventService;
  let mockNotificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService },
        { provide: NotificationService, useClass: MockNotificationService },
        {
          provide: MatDialogRef,
          useValue: {
            close: jest.fn(),
            backdropClick: jest.fn().mockReturnValue(of()),
            keydownEvents: jest.fn().mockReturnValue(of())
          }
        },
        {
          provide: MAT_DIALOG_DATA, useValue: {
            eventHandler: EMPTY_EVENT, isNewEvent: true
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventPanelComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();
  });

  it("should set selectedHandlerModule to first module", () => {
    expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
  });

  it("should save new event and reload events", () => {
    // set params for new event handler
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
  });
});
