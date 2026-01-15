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
import { EventService } from "../../../services/event/event.service";
import { MockNotificationService } from "../../../../testing/mock-services";
import { NotificationService } from "../../../services/notification/notification.service";

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
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventPanelComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("event", {
      id: 1,
      name: "TestHandler",
      handlermodule: "mockModule",
      active: true,
      event: ["eventA", "eventB"],
      action: "actionB",
      options: { opt3: "true" },
      conditions: { condA: true },
      position: 0
    });
    fixture.componentRef.setInput("isNewEvent", false);
    component.isEditMode.set(true);
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize event from input", () => {
    fixture.componentRef.setInput("event", {
      id: 2,
      name: "Handler2",
      handlermodule: "mockModule",
      active: false,
      event: ["eventC"],
      action: "actionB",
      options: { opt3: "val" },
      conditions: { condB: "val" },
      position: 1
    });
    fixture.detectChanges();
    expect(component.editEvent().id).toBe(2);
    expect(component.editEvent().name).toBe("Handler2");
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
    component.editEvent.set({ ...component.editEvent(), action: "actionA", options: {"opt1": null} });
    expect(component.validActionDefinition()).toBe(false);

    // option value is empty string
    component.editEvent.set({ ...component.editEvent(), action: "actionA", options: {"opt1": ""} });
    expect(component.validActionDefinition()).toBe(false);
  });

  it("validActionDefinition should be true if no action has no required options", () => {
    component.editEvent.set({ ...component.editEvent(), action: "actionB", options: {} });
    expect(component.validActionDefinition()).toBe(true);
  });

  it("validActionDefinition should be true if all required options are defined", () => {
    component.editEvent.set({ ...component.editEvent(), action: "actionA", options: {"opt1": 1} });
    expect(component.validActionDefinition()).toBe(true);
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
    component.editEvent.set({ ...component.editEvent(), name: ""});
    mockEventService.selectedHandlerModule.set("mockModule");
    expect(component.sectionValidity()["events"]).toBe(true);
    expect(component.sectionValidity()["action"]).toBe(true);
    expect(component.sectionValidity()["name"]).toBe(false);
    expect(component.sectionValidity()["handlerModule"]).toBe(true);
    expect(component.sectionValidity()["position"]).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("canSave should be false if position is not set", () => {
    component.editEvent.set({ ...component.editEvent(), position: ""});
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
    component.editEvent.set({ ...component.editEvent(), action: ""});
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
    component.editEvent.set({ ...component.editEvent(), name: "Changed" });
    component.cancelEdit();
    expect(component.isEditMode()).toBe(false);
    expect(component.editEvent().name).toBe("TestHandler");
  });

  it("should save event and reload events", () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    const snackBarSpy = jest.spyOn(mockNotificationService, "openSnackBar");
    // ensure effect is triggered to set the selected handler module in the service
    component.onPanelOpened();
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
      position: 0};
    expect(mockEventService.saveEventHandler).toHaveBeenCalledWith(convertedParams);
    expect(reloadSpy).toHaveBeenCalled();
    expect(component.isEditMode()).toBe(false);
    expect(snackBarSpy).toHaveBeenCalledWith("Event handler updated successfully.");
  });

  it("should delete event and reload events", () => {
    const reloadSpy = jest.spyOn(mockEventService.allEventsResource, "reload");
    component.deleteEvent();
    expect(mockEventService.deleteWithConfirmDialog).toHaveBeenCalled()
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("should toggle active and call enable/disable on service in read only mode", () => {
    component.isEditMode.set(false);
    component.toggleActive(true);
    expect(mockEventService.enableEvent).toHaveBeenCalledWith(1);
    component.toggleActive(false);
    expect(mockEventService.disableEvent).toHaveBeenCalledWith(1);
  });

  it("toggleActive should only edit event handler definition in edit mode", () => {
    component.isEditMode.set(true);
    // set active
    component.toggleActive(true);
    expect(component.editEvent().active).toBe(true)
    expect(mockEventService.enableEvent).not.toHaveBeenCalled();
    // set inactive
    component.toggleActive(false);
    expect(component.editEvent().active).toBe(false)
    expect(mockEventService.disableEvent).not.toHaveBeenCalled();
  });

  it("should set isExpanded to true when onPanelOpened is called", () => {
    component.isExpanded.set(false);
    component.onPanelOpened();
    expect(component.isExpanded()).toBe(true);
  });

  it("should set isExpanded to false when onPanelClosed is called", () => {
    component.isExpanded.set(true);
    component.onPanelClosed();
    expect(component.isExpanded()).toBe(false);
  });

  it("should set selectedHandlerModule when expanded and handlermodule is set (effect)", () => {
    fixture.componentRef.setInput("event", {
      id: 5,
      name: "Handler5",
      handlermodule: "testModule",
      active: true,
      event: ["eventA"],
      action: "actionA",
      options: {},
      conditions: {},
      position: 0
    });
    component.onPanelOpened();
    fixture.detectChanges(); // allow effect to run
    expect(mockEventService.selectedHandlerModule()).toBe("testModule");
  });

  it("should not set selectedHandlerModule if not expanded (effect)", () => {
    fixture.componentRef.setInput("event", {
      id: 6,
      name: "Handler6",
      handlermodule: "testModule2",
      active: true,
      event: ["eventB"],
      action: "actionB",
      options: {},
      conditions: {},
      position: 1
    });
    component.onPanelClosed();
    fixture.detectChanges(); // allow effect to run
    expect(mockEventService.selectedHandlerModule()).not.toBe("testModule2");
  });
});
