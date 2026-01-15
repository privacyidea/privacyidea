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

import { EventActionTabReadComponent } from "./event-action-tab-read.component";
import { EventService } from "../../../../../services/event/event.service";
import { MockEventService } from "../../../../../../testing/mock-services/mock-event-service";
import { ComponentFixture, TestBed } from "@angular/core/testing";

describe("EventActionTabReadComponent", () => {
  let component: EventActionTabReadComponent;
  let fixture: ComponentFixture<EventActionTabReadComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventActionTabReadComponent],
      providers: [
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventActionTabReadComponent);
    component = fixture.componentInstance;
    // Provide required inputs
    fixture.componentRef.setInput("action", "add_token_info");
    fixture.componentRef.setInput("options", { key: "test_key", value: "test_value", extra: "shouldBeIgnored" });
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should filter relevantOptions based on moduleActions", () => {
    // Only 'key' and 'value' are relevant for 'add_token_info'
    const relevant = component.relevantOptions();
    expect(relevant).toEqual({ key: "test_key", value: "test_value" });
    expect(relevant["extra"]).toBeUndefined();
  });

  it("should return empty relevantOptions if no matching keys", () => {
    fixture.componentRef.setInput("action", "actionB");
    fixture.componentRef.setInput("options", { foo: "bar" });
    fixture.detectChanges();
    expect(component.relevantOptions()).toEqual({});
  });

  it("should update relevantOptions when options input changes", () => {
    fixture.componentRef.setInput("options", { key: "new_key", value: "new_value" });
    fixture.detectChanges();
    expect(component.relevantOptions()).toEqual({ key: "new_key", value: "new_value" });
  });

  it("should update relevantOptions when action input changes", () => {
    fixture.componentRef.setInput("action", "actionA");
    fixture.componentRef.setInput("options", { opt1: true, opt2: 5, opt3: "foo" });
    fixture.detectChanges();
    expect(component.relevantOptions()).toEqual({ opt1: true, opt2: 5, opt3: "foo" });
  });
});
