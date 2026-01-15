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


describe("EventPanelNewComponent", () => {
  let component: EventPanelNewComponent;
  let fixture: ComponentFixture<EventPanelNewComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventPanelNewComponent],
      providers: [
        provideHttpClient(),
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventPanelNewComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    // Provide required inherited inputs
    fixture.componentRef.setInput("event", {
      id: "1",
      name: "TestHandlerNew",
      handlermodule: "anotherMockModule",
      active: true,
      event: ["eventA"],
      action: "actionA",
      options: { opt1: "val1" },
      conditions: { condA: true },
      position: "post",
      ordering: 0
    });
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
});
