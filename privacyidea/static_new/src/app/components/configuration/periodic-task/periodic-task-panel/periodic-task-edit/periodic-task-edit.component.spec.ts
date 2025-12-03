/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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

import { PeriodicTaskEditComponent } from "./periodic-task-edit.component";
import { provideHttpClient } from "@angular/common/http";
import { MockPeriodicTaskService } from "../../../../../../testing/mock-services/mock-periodic-task-service";
import { PeriodicTaskService } from "../../../../../services/periodic-task/periodic-task.service";
import { SystemService } from "../../../../../services/system/system.service";

describe("PeriodicTaskEditComponent", () => {
  let component: PeriodicTaskEditComponent;
  let fixture: ComponentFixture<PeriodicTaskEditComponent>;

  let mockTask = {
    id: "1",
    name: "Test Task",
    active: true,
    interval: "*/5 * * * *",
    nodes: ["node1"],
    taskmodule: "SimpleStats",
    retry_if_failed: true,
    ordering: 0,
    options: { hardware_tokens: "true", user_with_token: "true" }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskEditComponent],
      providers: [
        provideHttpClient(),
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService },
        { provide: SystemService, useValue: { nodes: () => [{ name: "node1", uuid: "node1" }] } }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("task", mockTask);
    fixture.componentRef.setInput("isNewTask", false);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should select an option", () => {
    component.onOptionSelection("total_tokens", { name: "total_tokens", description: "", type: "bool" });
    expect(component.selectedOption().name).toBe("total_tokens");
    expect(component.selectedOption().value).toBe("");
  });

  it("should add an option", () => {
    component.selectedOption.set({ name: "total_tokens", description: "", type: "bool" });
    component.addOption("true");
    expect(component.editTask().options["total_tokens"]).toBe("true");
  });

  it("should delete an option", () => {
    component.deleteOption("hardware_tokens");
    expect(component.editTask().options["hardware_tokens"]).toBeUndefined();
  });

  it("should detect boolean action", () => {
    expect(component.isBooleanAction("true")).toBe(true);
    expect(component.isBooleanAction("false")).toBe(true);
    expect(component.isBooleanAction("TRUE")).toBe(true);
    expect(component.isBooleanAction("False")).toBe(true);
    expect(component.isBooleanAction("yes")).toBe(false);
    expect(component.isBooleanAction("")).toBe(false);
  });

  it("should update nodes on selection change", () => {
    component.onNodeSelectionChange(["node1", "node2"]);
    expect(component.editTask().nodes).toEqual(["node1", "node2"]);
  });

  it("should update taskmodule on change", () => {
    component.onTaskModuleChange("EventCounter");
    expect(component.editTask().taskmodule).toBe("EventCounter");
  });
});
