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
import { PeriodicTaskPanelComponent } from "./periodic-task-panel.component";
import { EMPTY_PERIODIC_TASK, PeriodicTaskService } from "../../../../services/periodic-task/periodic-task.service";
import { provideHttpClient } from "@angular/common/http";
import { AuthService } from "../../../../services/auth/auth.service";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { MockPeriodicTaskService } from "../../../../../testing/mock-services/mock-periodic-task-service";

describe("PeriodicTaskPanelComponent", () => {
  let component: PeriodicTaskPanelComponent;
  let fixture: ComponentFixture<PeriodicTaskPanelComponent>;
  let task = {
    ...EMPTY_PERIODIC_TASK,
    id: "1",
    name: "Test Task",
    active: true,
    interval: "*/5 * * * *",
    nodes: ["localnode"],
    taskmodule: "SimpleStats",
    retry_if_failed: true,
    ordering: 0
  };
  let periodicTaskServiceMock: MockPeriodicTaskService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskPanelComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("task", task);
    periodicTaskServiceMock = TestBed.inject(PeriodicTaskService) as unknown as MockPeriodicTaskService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("savePeriodicTask does not save if not allowed", () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Edited" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = false;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    component.savePeriodicTask();
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("savePeriodicTask should save if allowed", () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Edited" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = true;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    component.savePeriodicTask();
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("cancelEdit should set isEditMode to false", () => {
    component.isEditMode.set(true);
    component.cancelEdit();
    expect(component.isEditMode()).toBe(false);
  });

  it("toggleActive should call enablePeriodicTask if activate is true", () => {
    const enableSpy = jest.spyOn(component.periodicTaskService, "enablePeriodicTask");
    component.toggleActive(true);
    expect(enableSpy).toHaveBeenCalledWith("1");
  });

  it("toggleActive fails if no task is provided", () => {
    fixture.componentRef.setInput("task", null);
    const enableSpy = jest.spyOn(component.periodicTaskService, "enablePeriodicTask");
    component.toggleActive(true);
    expect(enableSpy).not.toHaveBeenCalled();
  });

  it("toggleActive should call disablePeriodicTask if activate is false", () => {
    const disableSpy = jest.spyOn(component.periodicTaskService, "disablePeriodicTask");
    component.toggleActive(false);
    expect(disableSpy).toHaveBeenCalledWith("1");
  });

  it("deleteTask should reload resource", () => {
    const deleteSpy = jest.spyOn(periodicTaskServiceMock, "deleteWithConfirmDialog");
    component.deleteTask();
    expect(deleteSpy).toHaveBeenCalled();
  });
});
