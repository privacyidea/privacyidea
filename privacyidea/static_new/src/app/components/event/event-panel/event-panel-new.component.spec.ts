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

import { EventPanelNewComponent } from "./event-panel-new.component";
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MockEventService } from "../../../../testing/mock-services/mock-event-service";
import { EMPTY_EVENT, EventService } from "../../../services/event/event.service";
import { NotificationService } from '../../../services/notification/notification.service';
import { MockNotificationService } from "../../../../testing/mock-services";

describe("EventPanelNewComponent", () => {
  let component: EventPanelNewComponent;
  let fixture: ComponentFixture<EventPanelNewComponent>;
  let mockEventService: MockEventService;
  let mockNotificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventPanelNewComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventPanelNewComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    // Provide required inherited inputs
    fixture.componentRef.setInput("event", EMPTY_EVENT);
    fixture.componentRef.setInput("isNewEvent", true);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should be in edit mode when expanded", () => {
    component.isExpanded.set(true);
    expect(component.isEditMode()).toBe(true);
  });

  it("should not be in edit mode when not expanded", () => {
    component.isExpanded.set(false);
    expect(component.isEditMode()).toBe(false);
  });

  it("should set selectedHandlerModule to first module when expanded and none selected (effect)", () => {
    mockEventService.selectedHandlerModule.set(null);
    fixture.componentRef.setInput("event", EMPTY_EVENT);
    component.isExpanded.set(true);
    fixture.detectChanges();
    expect(mockEventService.selectedHandlerModule()).toBe("mockModule");
  });

  it("should not overwrite selectedHandlerModule if already set (effect)", () => {
    mockEventService.selectedHandlerModule.set("anotherMockModule");
    component.isExpanded.set(true);
    fixture.detectChanges();
    expect(mockEventService.selectedHandlerModule()).toBe("anotherMockModule");
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
    const editEventSpy = jest.spyOn(component.editEvent, "set");
    const panelCloseSpy = jest.spyOn(component.panel, "close");
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
    expect(component.isEditMode()).toBe(false);
    expect(editEventSpy).toHaveBeenCalledWith(EMPTY_EVENT);
    expect(panelCloseSpy).toHaveBeenCalled();
    expect(snackBarSpy).toHaveBeenCalledWith("Event handler created successfully.");
  });
});
