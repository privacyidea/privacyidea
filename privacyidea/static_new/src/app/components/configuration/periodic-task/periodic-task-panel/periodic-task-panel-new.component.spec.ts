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

import { PeriodicTaskPanelNewComponent } from "./periodic-task-panel-new.component";
import { PeriodicTaskPanelComponent } from "./periodic-task-panel.component";
import { EMPTY_PERIODIC_TASK, PeriodicTaskService } from "../../../../services/periodic-task/periodic-task.service";
import { provideHttpClient } from "@angular/common/http";
import { AuthService } from "../../../../services/auth/auth.service";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { MockPeriodicTaskService } from "../../../../../testing/mock-services/mock-periodic-task-service";

describe("PeriodicTaskPanelNewComponent", () => {
  let component: PeriodicTaskPanelNewComponent;
  let fixture: ComponentFixture<PeriodicTaskPanelNewComponent>;
  let periodicTaskServiceMock: MockPeriodicTaskService;
  let task = {...EMPTY_PERIODIC_TASK};

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskPanelNewComponent, PeriodicTaskPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskPanelNewComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("task", task);
    periodicTaskServiceMock = TestBed.inject(PeriodicTaskService) as unknown as MockPeriodicTaskService;
    fixture.detectChanges();
  });


  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should call savePeriodicTask, reload resource, close panel, and emit taskSaved if allowed", () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "EditedNew" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = true;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    const emitSpy = jest.spyOn(component.taskSaved, "emit");
    const panelCloseSpy = jest.spyOn(component.panel, "close");
    component.savePeriodicTask();
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).toHaveBeenCalledWith({ ...EMPTY_PERIODIC_TASK, name: "EditedNew" });
    expect(reloadSpy).toHaveBeenCalled();
    expect(panelCloseSpy).toHaveBeenCalled();
    expect(emitSpy).toHaveBeenCalled();
  });

  it("should not call savePeriodicTask, reload resource, close panel, and emit taskSaved if not allowed", () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "EditedNew" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = false;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    const emitSpy = jest.spyOn(component.taskSaved, "emit");
    const panelCloseSpy = jest.spyOn(component.panel, "close");
    component.savePeriodicTask();
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
    expect(panelCloseSpy).not.toHaveBeenCalled();
    expect(emitSpy).not.toHaveBeenCalled();
  });
});
