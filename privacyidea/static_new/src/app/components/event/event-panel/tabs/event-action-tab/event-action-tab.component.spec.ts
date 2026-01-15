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

import { EventActionTabComponent } from "./event-action-tab.component";
import { EventService } from "../../../../../services/event/event.service";
import { MockEventService } from "../../../../../../testing/mock-services/mock-event-service";
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { AuthService } from "../../../../../services/auth/auth.service";
import { MockAuthService } from "../../../../../../testing/mock-services/mock-auth-service";

describe("EventActionTabComponent", () => {
  let component: EventActionTabComponent;
  let fixture: ComponentFixture<EventActionTabComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventActionTabComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: EventService, useClass: MockEventService }]
    }).compileComponents();

    fixture = TestBed.createComponent(EventActionTabComponent);
    component = fixture.componentInstance;
    // Provide required inputs
    fixture.componentRef.setInput("action", "add_token_info");
    fixture.componentRef.setInput("options", { "key": "test_key", "value": "test_value" });
    fixture.componentRef.setInput("isEditMode", true);
    component.newAction = { emit: jest.fn() } as any;
    component.newOptions = { emit: jest.fn() } as any;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize selectedAction from input", () => {
    component.selectedAction.set("");
    component.ngOnInit();
    expect(component.selectedAction()).toBe("add_token_info");
  });

  it("should emit newAction and reset options on action selection change", () => {
    component.selectedAction.set("actionB");
    component.selectedOptions.set({ opt3: "foo" });
    component.onActionSelectionChange();
    expect(component.newAction.emit).toHaveBeenCalledWith("actionB");
    expect(component.selectedOptions()).toEqual({});
    expect(component.newOptions.emit).toHaveBeenCalledWith({});
  });

  it("should update selectedOptions and emit on option change", () => {
    component.selectedOptions.set({ opt1: false });
    component.onOptionChange("opt2", "test");
    const newOptions = { opt1: false, opt2: "test" };
    expect(component.selectedOptions()).toEqual(newOptions);
    expect(component.newOptions.emit).toHaveBeenCalledWith(newOptions);
  });

  it("actionOptions() should return empty dict if no action is selected", () => {
    component.selectedAction.set("");
    const opts = component.actionOptions();
    expect(opts).toMatchObject({});
  });

  it("actionOptions() should return options for selected action", () => {
    component.selectedAction.set("actionA");
    const opts = component.actionOptions();
    expect(opts["opt1"].type).toBe("bool");
    expect(opts["opt2"].type).toBe("int");
  });

  it("checkOptionVisibility returns true if no visibleIf", () => {
    component.selectedAction.set("actionA");
    expect(component.checkOptionVisibility("opt1")).toBe(true);
  });

  it("checkOptionVisibility returns true if visibleIf is set and value matches", () => {
    component.selectedAction.set("actionA");
    component.selectedOptions.set({ opt1: true, opt2: 3 });
    expect(component.checkOptionVisibility("opt3")).toBe(true);
  });

  it("checkOptionVisibility returns false if visibleIf is set and value does not match", () => {
    component.selectedAction.set("actionA");
    component.selectedOptions.set({ opt1: true, opt2: 1 });
    expect(component.checkOptionVisibility("opt3")).toBe(false);
  });

  it("checkOptionVisibility returns true if visibleIf is set, but not visibleValue and dependent value is set", () => {
    component.selectedAction.set("actionA");
    component.selectedOptions.set({ opt1: true });
    expect(component.checkOptionVisibility("opt2")).toBe(true);
  });
});
