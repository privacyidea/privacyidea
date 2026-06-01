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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import {
  HostsMachineResolver,
  HostsMachineResolverData,
  MachineResolverService
} from "@services/machine-resolver/machine-resolver.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockContentService, MockNotificationService } from "@testing/mock-services";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockMachineResolverService } from "@testing/mock-services/mock-machine-resolver-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { of } from "rxjs";
import { MachineResolverPanelEditComponent } from "./machine-resolver-panel-edit.component";

@Component({
  standalone: true,
  selector: "app-machine-resolver-hosts-tab",
  template: ""
})
class MachineResolverHostsTabComponent {}

@Component({
  standalone: true,
  selector: "app-machine-resolver-ldap-tab",
  template: ""
})
class MachineResolverLdapTabComponent {}

describe("MachineResolverPanelEditComponent", () => {
  let component: MachineResolverPanelEditComponent;
  let fixture: ComponentFixture<MachineResolverPanelEditComponent>;
  let machineResolverServiceMock: MockMachineResolverService;
  let dialogServiceMock: MockDialogService;
  let contentServiceMock: MockContentService;
  let pendingChangesService: MockPendingChangesService;

  const machineResolver: HostsMachineResolver = {
    resolvername: "test",
    type: "hosts",
    data: {
      resolver: "test",
      type: "hosts",
      filename: "testfile"
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverPanelEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    })
      .overrideComponent(MachineResolverPanelEditComponent, {
        set: {
          imports: [MachineResolverHostsTabComponent, MachineResolverLdapTabComponent]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(MachineResolverPanelEditComponent);
    component = fixture.componentInstance;
    machineResolverServiceMock = TestBed.inject(MachineResolverService) as unknown as MockMachineResolverService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    fixture.componentRef.setInput("originalMachineResolver", machineResolver);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should enter edit mode", () => {
    expect(component.isEditMode()).toBeFalsy();
    component.isEditMode.set(true);
    expect(component.isEditMode()).toBeTruthy();
  });

  it("should change machineResolver type", () => {
    component.isEditMode.set(true);
    component.onMachineResolverTypeChange("ldap");
    expect(component.editedMachineResolver().type).toBe("ldap");
    expect(component.editedMachineResolver().data.type).toBe("ldap");
  });

  it("should change resolvername", () => {
    component.isEditMode.set(true);
    component.onResolvernameChange("newName");
    expect(component.editedMachineResolver().resolvername).toBe("newName");
    expect(component.editedMachineResolver().data.resolver).toBe("newName");
  });

  it("should update resolver data", () => {
    component.isEditMode.set(true);
    const newData: HostsMachineResolverData = {
      type: "hosts",
      filename: "newfile",
      resolver: "test"
    };
    component.onUpdateResolverData(newData);
    expect(component.editedMachineResolver().data).toEqual(newData);
  });

  it("should save machineResolver successfully", async () => {
    machineResolverServiceMock.postTestMachineResolver.mockReturnValue(Promise.resolve(null));
    machineResolverServiceMock.postMachineResolver.mockReturnValue(Promise.resolve(null));
    component.isEditMode.set(true);
    await component.saveMachineResolver();
    expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalled();
    expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
    expect(component.isEditMode()).toBeFalsy();
  });

  it("should save machineResolver despite test failure if confirmed", async () => {
    machineResolverServiceMock.postTestMachineResolver.mockReturnValue(Promise.reject(Error("post-failed")));
    machineResolverServiceMock.postMachineResolver.mockReturnValue(Promise.resolve(null));
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(true));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component.isEditMode.set(true);
    await component.saveMachineResolver();
    expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalled();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
    expect(component.isEditMode()).toBeFalsy();
  });

  it("should not save machineResolver if test fails and not confirmed", async () => {
    machineResolverServiceMock.postTestMachineResolver.mockReturnValue(Promise.reject(Error("post-failed")));
    machineResolverServiceMock.postMachineResolver.mockReturnValue(Promise.resolve(null));
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(false));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component.isEditMode.set(true);
    await component.saveMachineResolver();
    expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalled();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(machineResolverServiceMock.postMachineResolver).not.toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy(); // Should remain in edit mode
  });

  it("should not save machineResolver if post fails", async () => {
    machineResolverServiceMock.postTestMachineResolver.mockReturnValue(Promise.resolve(null));
    machineResolverServiceMock.postMachineResolver.mockReturnValue(Promise.reject(Error("save-failed")));
    component.isEditMode.set(true);
    await component.saveMachineResolver();
    expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalled();
    expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy(); // Should remain in edit mode
  });

  it("should delete machineResolver if confirmed", async () => {
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(true));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    machineResolverServiceMock.deleteMachineResolver.mockReturnValue(Promise.resolve(null));
    await component.deleteMachineResolver();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(machineResolverServiceMock.deleteMachineResolver).toHaveBeenCalledWith("test");
  });

  it("should not delete machineResolver if cancelled", async () => {
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(false));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    machineResolverServiceMock.deleteMachineResolver.mockReturnValue(Promise.resolve(null));
    await component.deleteMachineResolver();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(machineResolverServiceMock.deleteMachineResolver).not.toHaveBeenCalled();
  });

  it("should cancel edit mode if not edited", () => {
    component.isEditMode.set(true);
    TestBed.tick();
    component.cancelEditMode();
    expect(component.isEditMode()).toBeFalsy();
    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
  });

  it("should cancel edit mode if edited and dialog confirmed", async () => {
    component.isEditMode.set(true);
    component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
    TestBed.tick();
    expect(component.isEdited()).toBeTruthy();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of("discard"));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component.cancelEditMode();
    await Promise.resolve();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(component.isEditMode()).toBeFalsy();
    expect(component.editedMachineResolver().type).toBe("hosts");
  });

  it("should not cancel edit mode if edited and dialog cancelled", () => {
    component.isEditMode.set(true);
    component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
    TestBed.tick();
    expect(component.isEdited()).toBeTruthy();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(null));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component.cancelEditMode();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy();
    expect(component.editedMachineResolver().type).toBe("ldap");
  });

  it("should not save when cancelEditMode save-exit is picked but canSave is false", async () => {
    component.isEditMode.set(true);
    component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
    component.dataValidatorSignal.set(() => false);
    TestBed.tick();
    expect(component.canSaveMachineResolver()).toBeFalsy();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of("save-exit"));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    const saveSpy = jest.spyOn(component, "saveMachineResolver");
    component.cancelEditMode();
    await Promise.resolve();
    expect(saveSpy).not.toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy();
  });

  it("should save and exit when cancelEditMode dialog returns save-exit", async () => {
    component.isEditMode.set(true);
    component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
    component.dataValidatorSignal.set(() => true);
    TestBed.tick();
    expect(component.canSaveMachineResolver()).toBeTruthy();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of("save-exit"));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    const saveSpy = jest.spyOn(component, "saveMachineResolver").mockResolvedValue(true);
    component.cancelEditMode();
    await Promise.resolve();
    expect(saveSpy).toHaveBeenCalled();
  });

  describe("handleCollapse", () => {
    it("just closes when not edited", () => {
      component.isEditMode.set(true);
      const panel = { close: jest.fn(), open: jest.fn() } as any;
      component.handleCollapse(panel);
      expect(component.isEditMode()).toBeFalsy();
      expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
    });

    it("opens panel back when dialog is cancelled", async () => {
      component.isEditMode.set(true);
      component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
      TestBed.tick();
      const panel = { close: jest.fn(), open: jest.fn() } as any;
      const dialogRefMock = new MockMatDialogRef();
      dialogRefMock.afterClosed.mockReturnValue(of(null));
      dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
      component.handleCollapse(panel);
      await Promise.resolve();
      expect(panel.open).toHaveBeenCalled();
      expect(panel.close).not.toHaveBeenCalled();
      expect(component.isEditMode()).toBeTruthy();
    });

    it("closes panel and discards on discard", async () => {
      component.isEditMode.set(true);
      component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
      TestBed.tick();
      const panel = { close: jest.fn(), open: jest.fn() } as any;
      const dialogRefMock = new MockMatDialogRef();
      dialogRefMock.afterClosed.mockReturnValue(of("discard"));
      dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
      component.handleCollapse(panel);
      await Promise.resolve();
      expect(panel.close).toHaveBeenCalled();
      expect(component.isEditMode()).toBeFalsy();
    });

    it("saves and closes panel when save-exit succeeds", async () => {
      component.isEditMode.set(true);
      component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
      component.dataValidatorSignal.set(() => true);
      TestBed.tick();
      const panel = { close: jest.fn(), open: jest.fn() } as any;
      const dialogRefMock = new MockMatDialogRef();
      dialogRefMock.afterClosed.mockReturnValue(of("save-exit"));
      dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
      const saveSpy = jest.spyOn(component, "saveMachineResolver").mockResolvedValue(true);
      component.handleCollapse(panel);
      await Promise.resolve();
      await Promise.resolve();
      expect(saveSpy).toHaveBeenCalled();
      expect(panel.close).toHaveBeenCalled();
    });

    it("reopens panel when save-exit is picked but canSave is false", async () => {
      component.isEditMode.set(true);
      component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
      component.dataValidatorSignal.set(() => false);
      TestBed.tick();
      const panel = { close: jest.fn(), open: jest.fn() } as any;
      const dialogRefMock = new MockMatDialogRef();
      dialogRefMock.afterClosed.mockReturnValue(of("save-exit"));
      dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
      const saveSpy = jest.spyOn(component, "saveMachineResolver");
      component.handleCollapse(panel);
      await Promise.resolve();
      expect(panel.open).toHaveBeenCalled();
      expect(saveSpy).not.toHaveBeenCalled();
    });

    it("reopens panel when save-exit save fails", async () => {
      component.isEditMode.set(true);
      component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
      component.dataValidatorSignal.set(() => true);
      TestBed.tick();
      const panel = { close: jest.fn(), open: jest.fn() } as any;
      const dialogRefMock = new MockMatDialogRef();
      dialogRefMock.afterClosed.mockReturnValue(of("save-exit"));
      dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
      jest.spyOn(component, "saveMachineResolver").mockResolvedValue(false);
      component.handleCollapse(panel);
      await Promise.resolve();
      await Promise.resolve();
      expect(panel.open).toHaveBeenCalled();
      expect(panel.close).not.toHaveBeenCalled();
    });
  });

  describe("check if machineResolver can be saved", () => {
    it("when data and resolvername are valid", () => {
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => true);
      component.editedMachineResolver.set({ ...machineResolver, resolvername: "test" });
      expect(component.canSaveMachineResolver()).toBeTruthy();
    });

    it("when data is valid but resolvername is empty", () => {
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => true);
      component.editedMachineResolver.set({ ...machineResolver, resolvername: " " }); // Should not be empty (trimmed)
      expect(component.canSaveMachineResolver()).toBeFalsy();
    });

    it("when data is invalid but resolvername is valid", () => {
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => false);
      component.editedMachineResolver.set({ ...machineResolver, resolvername: "test" });
      expect(component.canSaveMachineResolver()).toBeFalsy();
    });

    it("when both data and resolvername are invalid", () => {
      component.dataValidatorSignal.set(() => false);
      component.editedMachineResolver.set({ ...machineResolver, resolvername: " " }); // Should not be empty (trimmed)
      expect(component.canSaveMachineResolver()).toBeFalsy();
    });
  });

  describe("expansion logic", () => {
    it("should be expanded if contentService matches resolvername", () => {
      contentServiceMock.machineResolver.set("test");
      TestBed.tick();
      expect(component.expanded()).toBeTruthy();
    });

    it("should not be expanded if contentService does not match resolvername", () => {
      contentServiceMock.machineResolver.set("other");
      TestBed.tick();
      expect(component.expanded()).toBeFalsy();
    });

    it("should clear signal when collapsed", () => {
      contentServiceMock.machineResolver.set("test");
      component.handleCollapse({} as any);
      expect(contentServiceMock.machineResolver()).toBe("");
    });
  });

  describe("pending changes", () => {
    it("does not register before entering edit mode with diff", () => {
      expect(pendingChangesService.registerHasChanges).not.toHaveBeenCalled();
      expect(pendingChangesService.registerSave).not.toHaveBeenCalled();
    });

    it("registers hasChanges, validChanges, and save once editing with diff", () => {
      component.isEditMode.set(true);
      component.editedMachineResolver.update((mr) => ({ ...mr, data: { ...mr.data, filename: "changed" } }));
      fixture.detectChanges();
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("saveMachineResolver resolves true on successful post", async () => {
      jest.spyOn(machineResolverServiceMock, "postTestMachineResolver").mockResolvedValue(undefined as any);
      jest.spyOn(machineResolverServiceMock, "postMachineResolver").mockResolvedValue(undefined as any);
      component.isEditMode.set(true);
      const result = await component.saveMachineResolver();
      expect(result).toBe(true);
      expect(component.isEditMode()).toBe(false);
    });

    it("saveMachineResolver resolves false when test fails and user does not confirm", async () => {
      jest.spyOn(machineResolverServiceMock, "postTestMachineResolver").mockRejectedValue(new Error("post-failed"));
      const dialogRef = new MockMatDialogRef();
      jest.spyOn(dialogRef, "afterClosed").mockReturnValue(of(false));
      dialogServiceMock.openDialog = jest.fn().mockReturnValue(dialogRef);
      const result = await component.saveMachineResolver();
      expect(result).toBe(false);
    });

    it("saveMachineResolver resolves false when test fails with non post-failed error", async () => {
      jest.spyOn(machineResolverServiceMock, "postTestMachineResolver").mockRejectedValue(new Error("other-error"));
      const result = await component.saveMachineResolver();
      expect(result).toBe(false);
    });
  });
});
