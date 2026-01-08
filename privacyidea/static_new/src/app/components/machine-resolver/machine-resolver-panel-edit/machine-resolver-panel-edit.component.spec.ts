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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import {
  HostsMachineResolver,
  HostsMachineResolverData,
  MachineResolverService
} from "../../../services/machine-resolver/machine-resolver.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { MockNotificationService } from "../../../../testing/mock-services";
import { MockMachineResolverService } from "../../../../testing/mock-services/mock-machine-resolver-service";
import { Component } from "@angular/core";
import { MockDialogService } from "../../../../testing/mock-services/mock-dialog-service";
import { MachineResolverPanelEditComponent } from "./machine-resolver-panel-edit.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockMatDialogRef } from "../../../../testing/mock-mat-dialog-ref";
import { of } from "rxjs";

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
  let notificationServiceMock: MockNotificationService;

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
      imports: [MachineResolverPanelEditComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService }
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
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;

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
    TestBed.flushEffects();
    component.cancelEditMode();
    expect(component.isEditMode()).toBeFalsy();
    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
  });

  it("should cancel edit mode if edited and dialog confirmed", async () => {
    component.isEditMode.set(true);
    component.editedMachineResolver.set({ ...machineResolver, type: "ldap" });
    TestBed.flushEffects();
    expect(component.isEdited()).toBeTruthy();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(true));
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
    TestBed.flushEffects();
    expect(component.isEdited()).toBeTruthy();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(false));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component.cancelEditMode();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(component.isEditMode()).toBeTruthy();
    expect(component.editedMachineResolver().type).toBe("ldap");
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
      component.isEditMode.set(true);
      component.dataValidatorSignal.set(() => false);
      component.editedMachineResolver.set({ ...machineResolver, resolvername: " " }); // Should not be empty (trimmed)
      expect(component.canSaveMachineResolver()).toBeFalsy();
    });
  });
});
