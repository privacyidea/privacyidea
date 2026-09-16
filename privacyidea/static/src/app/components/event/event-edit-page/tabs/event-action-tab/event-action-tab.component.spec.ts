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
import { OutputEmitterRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { AuthService } from "@services/auth/auth.service";
import { EventService } from "@services/event/event.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockEventService } from "@testing/mock-services/mock-event-service";
import { EventActionOptionValues, EventActionTabComponent } from "./event-action-tab.component";

describe("EventActionTabComponent", () => {
  let component: EventActionTabComponent;
  let fixture: ComponentFixture<EventActionTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventActionTabComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: EventService, useClass: MockEventService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EventActionTabComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("action", "add_token_info");
    fixture.componentRef.setInput("options", { key: "test_key", value: "test_value" });
    component.newAction = { emit: jest.fn() } as unknown as OutputEmitterRef<string>;
    component.newOptions = { emit: jest.fn() } as unknown as OutputEmitterRef<EventActionOptionValues>;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize selectedAction from input", () => {
    expect(component.selectedAction()).toBe("add_token_info");
  });

  it("should reset options on action selection change and emit changes", () => {
    component.selectedAction.set("actionB");
    fixture.detectChanges();
    expect(Object.keys(component.selectedOptions())).toEqual(["opt3"]);
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt3: "" });
  });

  it("should update selectedOptions and emit on option change", () => {
    component.setOption("key", "another_key");
    component.setOption("value", "");
    fixture.detectChanges();

    expect(component.selectedOptions()).toEqual({ key: "another_key", value: "" });
    expect(component.newOptions.emit).toHaveBeenCalledWith({ key: "another_key", value: "" });
  });

  it("should also emit empty options", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    expect(Object.keys(component.selectedOptions())).toEqual(["opt1", "opt2", "opt3"]);
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt1: "", opt2: "", opt3: "" });

    component.setOption("opt3", "newValue");
    fixture.detectChanges();
    expect(component.selectedOptions()).toEqual({ opt1: "", opt2: "", opt3: "newValue" });
    expect(component.newOptions.emit).toHaveBeenCalledWith({ opt1: "", opt2: "", opt3: "newValue" });
  });

  it("onActionSelectionChange should emit selected action", () => {
    component.onActionSelectionChange("actionB");
    expect(component.newAction.emit).toHaveBeenCalledWith("actionB");

    component.onActionSelectionChange("");
    expect(component.newAction.emit).toHaveBeenCalledWith("");
  });

  it("actionOptions() should return empty dict if no action is selected", () => {
    component.selectedAction.set("");
    fixture.componentRef.setInput("action", "");
    fixture.detectChanges();
    const opts = component.actionOptions();
    expect(opts).toMatchObject({});
  });

  it("actionOptions() should return options for selected action", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    const opts = component.actionOptions();
    expect(opts["opt1"].type).toBe("bool");
    expect(opts["opt2"].type).toBe("int");
  });

  it("checkOptionVisibility returns true if no visibleIf", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt1")).toBe(true);
  });

  it("checkOptionVisibility returns true if visibleIf is set and value matches", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true, opt2: "3" });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt3")).toBe(true);
  });

  it("checkOptionVisibility returns false if visibleIf is set and value does not match", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true, opt2: "1" });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt3")).toBe(false);
  });

  it("checkOptionVisibility returns true if visibleIf is set, but not visibleValue and dependent value is set", () => {
    component.selectedAction.set("actionA");
    fixture.detectChanges();
    component.selectedOptions.set({ opt1: true });
    fixture.detectChanges();
    expect(component.checkOptionVisibility("opt2")).toBe(true);
  });
});
