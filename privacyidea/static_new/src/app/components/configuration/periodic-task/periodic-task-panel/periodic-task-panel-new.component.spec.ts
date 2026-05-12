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

import { ComponentFixture, TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { EMPTY_PERIODIC_TASK, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockPeriodicTaskService } from "@testing/mock-services/mock-periodic-task-service";
import { of } from "rxjs";
import { PeriodicTaskPanelNewComponent } from "./periodic-task-panel-new.component";
import { PeriodicTaskPanelComponent } from "./periodic-task-panel.component";

describe("PeriodicTaskPanelNewComponent", () => {
  let component: PeriodicTaskPanelNewComponent;
  let fixture: ComponentFixture<PeriodicTaskPanelNewComponent>;
  let periodicTaskServiceMock: MockPeriodicTaskService;
  let dialogServiceMock: MockDialogService;
  let task = { ...EMPTY_PERIODIC_TASK };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskPanelNewComponent, PeriodicTaskPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskPanelNewComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("task", task);
    periodicTaskServiceMock = TestBed.inject(PeriodicTaskService) as unknown as MockPeriodicTaskService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should call savePeriodicTask, reload resource, close panel, and emit taskSaved if allowed", async () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "EditedNew" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = true;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    const emitSpy = jest.spyOn(component.taskSaved, "emit");
    const panelCloseSpy = jest.spyOn(component.panel, "close");
    await component.savePeriodicTask();
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).toHaveBeenCalledWith({ ...EMPTY_PERIODIC_TASK, name: "EditedNew" });
    expect(reloadSpy).toHaveBeenCalled();
    expect(panelCloseSpy).toHaveBeenCalled();
    expect(emitSpy).toHaveBeenCalled();
  });

  it("should not call savePeriodicTask, reload resource, close panel, and emit taskSaved if not allowed", async () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "EditedNew" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = false;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    const emitSpy = jest.spyOn(component.taskSaved, "emit");
    const panelCloseSpy = jest.spyOn(component.panel, "close");
    await component.savePeriodicTask();
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
    expect(panelCloseSpy).not.toHaveBeenCalled();
    expect(emitSpy).not.toHaveBeenCalled();
  });

  it("cancelEdit closes silently when not edited", () => {
    component.editComponent = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK }) } as any;
    const editTaskSetSpy = jest.fn();
    (component.editComponent as any).editTask.set = editTaskSetSpy;
    const panelCloseSpy = jest.spyOn(component.panel, "close");

    component.cancelEdit();

    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
    expect(component.isEditMode()).toBe(false);
    expect(editTaskSetSpy).toHaveBeenCalledWith(EMPTY_PERIODIC_TASK);
    expect(panelCloseSpy).toHaveBeenCalled();
  });

  it("cancelEdit opens save-and-exit dialog when edited and discards on confirm", () => {
    component.editComponent = {
      editTask: Object.assign(jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Changed" }), {
        set: jest.fn()
      })
    } as any;
    const dialogRef = new MockMatDialogRef();
    jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("discard"));
    dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);
    const panelCloseSpy = jest.spyOn(component.panel, "close");

    component.cancelEdit();

    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(component.isEditMode()).toBe(false);
    expect(panelCloseSpy).toHaveBeenCalled();
  });

  it("cancelEdit stays open when save-and-exit dialog is dismissed", () => {
    component.editComponent = {
      editTask: Object.assign(jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Changed" }), {
        set: jest.fn()
      })
    } as any;
    component.isEditMode.set(true);
    const dialogRef = new MockMatDialogRef();
    jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of(null));
    dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);
    const panelCloseSpy = jest.spyOn(component.panel, "close");

    component.cancelEdit();

    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(component.isEditMode()).toBe(true);
    expect(panelCloseSpy).not.toHaveBeenCalled();
  });

  it("cancelEdit triggers savePeriodicTask on save-exit when canSave is true", async () => {
    component.editComponent = {
      editTask: Object.assign(jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Changed" }), {
        set: jest.fn()
      })
    } as any;
    component.canSave = true;
    const dialogRef = new MockMatDialogRef();
    jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("save-exit"));
    dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);
    const saveSpy = jest.spyOn(component, "savePeriodicTask").mockResolvedValue(true);

    component.cancelEdit();
    await Promise.resolve();

    expect(saveSpy).toHaveBeenCalled();
  });

  it("cancelEdit does not save on save-exit when canSave is false", async () => {
    component.editComponent = {
      editTask: Object.assign(jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Changed" }), {
        set: jest.fn()
      })
    } as any;
    component.canSave = false;
    const dialogRef = new MockMatDialogRef();
    jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of("save-exit"));
    dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);
    const saveSpy = jest.spyOn(component, "savePeriodicTask").mockResolvedValue(true);
    const panelCloseSpy = jest.spyOn(component.panel, "close");

    component.cancelEdit();
    await Promise.resolve();

    expect(saveSpy).not.toHaveBeenCalled();
    expect(panelCloseSpy).not.toHaveBeenCalled();
  });
});
