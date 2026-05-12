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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { EMPTY_PERIODIC_TASK, PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockPeriodicTaskService } from "@testing/mock-services/mock-periodic-task-service";
import { of } from "rxjs";
import { PeriodicTaskPanelComponent } from "./periodic-task-panel.component";

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
  let dialogServiceMock: MockDialogService;
  let pendingChangesService: MockPendingChangesService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskPanelComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: PeriodicTaskService, useClass: MockPeriodicTaskService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskPanelComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("task", task);
    periodicTaskServiceMock = TestBed.inject(PeriodicTaskService) as unknown as MockPeriodicTaskService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("savePeriodicTask resolves false and does not save if not allowed", async () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Edited" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = false;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    const result = await component.savePeriodicTask();
    expect(result).toBe(false);
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).not.toHaveBeenCalled();
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it("savePeriodicTask resolves true and saves if allowed", async () => {
    const editComponentMock = { editTask: jest.fn().mockReturnValue({ ...EMPTY_PERIODIC_TASK, name: "Edited" }) };
    component.editComponent = editComponentMock as any;
    component.canSave = true;
    const saveSpy = jest.spyOn(periodicTaskServiceMock, "savePeriodicTask");
    const reloadSpy = jest.spyOn(periodicTaskServiceMock.periodicTasksResource, "reload");
    const result = await component.savePeriodicTask();
    expect(result).toBe(true);
    expect(editComponentMock.editTask).toHaveBeenCalled();
    expect(saveSpy).toHaveBeenCalled();
    expect(reloadSpy).toHaveBeenCalled();
    expect(component.isEditMode()).toBe(false);
  });

  it("cancelEdit should set isEditMode to false when task is not edited", () => {
    component.isEditMode.set(true);
    component.editComponent = { editTask: jest.fn().mockReturnValue({ ...task }) } as any;
    component.cancelEdit();
    expect(component.isEditMode()).toBe(false);
    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
  });

  it("cancelEdit should open confirmation dialog when task has been edited", () => {
    component.isEditMode.set(true);
    const dialogRef = new MockMatDialogRef();
    jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of(false));
    dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);
    component.editComponent = { editTask: jest.fn().mockReturnValue({ ...task, name: "Changed Name" }) } as any;

    component.cancelEdit();

    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(component.isEditMode()).toBe(true);
  });

  it("cancelEdit should set isEditMode to false after user confirms discard in dialog", () => {
    component.isEditMode.set(true);
    const dialogRef = new MockMatDialogRef();
    jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of(true));
    dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);
    component.editComponent = { editTask: jest.fn().mockReturnValue({ ...task, name: "Changed Name" }) } as any;

    component.cancelEdit();

    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
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

  describe("pending changes", () => {
    it("does not register anything before entering edit mode", () => {
      expect(pendingChangesService.registerHasChanges).not.toHaveBeenCalled();
      expect(pendingChangesService.registerValidChanges).not.toHaveBeenCalled();
      expect(pendingChangesService.registerSave).not.toHaveBeenCalled();
    });

    it("registers hasChanges, validChanges, and save once edit mode becomes true", () => {
      component.isEditMode.set(true);
      fixture.detectChanges();
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("hasChanges callback reflects dirty edit state, not just edit mode", () => {
      component.isEditMode.set(true);
      fixture.detectChanges();
      const fn = (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;

      component.editComponent = { editTask: jest.fn().mockReturnValue({ ...task }) } as any;
      expect(fn()).toBe(false);

      component.editComponent = { editTask: jest.fn().mockReturnValue({ ...task, name: "Changed" }) } as any;
      expect(fn()).toBe(true);

      component.isEditMode.set(false);
      expect(fn()).toBe(false);
    });

    it("validChanges callback reflects canSave", () => {
      component.isEditMode.set(true);
      fixture.detectChanges();
      const fn = (pendingChangesService.registerValidChanges as jest.Mock).mock.calls[0][0] as () => boolean;
      component.canSave = true;
      expect(fn()).toBe(true);
      component.canSave = false;
      expect(fn()).toBe(false);
    });
  });
});
