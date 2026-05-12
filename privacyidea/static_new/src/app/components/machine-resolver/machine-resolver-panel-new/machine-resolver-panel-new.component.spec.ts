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
import { DialogService } from "@services/dialog/dialog.service";
import {
    HostsMachineResolverData,
    LdapMachineResolverData,
    MachineResolverService
} from "@services/machine-resolver/machine-resolver.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { MockMachineResolverService } from "@testing/mock-services/mock-machine-resolver-service";
import { of } from "rxjs";
import { MachineResolverPanelNewComponent } from "./machine-resolver-panel-new.component";

describe("MachineResolverPanelNewComponent", () => {
  let component: MachineResolverPanelNewComponent;
  let fixture: ComponentFixture<MachineResolverPanelNewComponent>;
  let machineResolverServiceMock: MockMachineResolverService;
  let dialogServiceMock: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachineResolverPanelNewComponent, NoopAnimationsModule],
      providers: [
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();
    fixture = TestBed.createComponent(MachineResolverPanelNewComponent);
    component = fixture.componentInstance;
    machineResolverServiceMock = TestBed.inject(MachineResolverService) as unknown as MockMachineResolverService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should change machineResolver type", () => {
    component.onMachineResolverTypeChange("ldap");
    expect(component.newMachineResolver().type).toBe("ldap");
    expect(component.newMachineResolver().data.type).toBe("ldap");
  });

  it("should change resolvername", () => {
    component.onResolvernameChange("newName");
    expect(component.newMachineResolver().resolvername).toBe("newName");
    expect(component.newMachineResolver().data.resolver).toBe("newName");
  });

  it("should update resolver data", () => {
    const newData: HostsMachineResolverData = {
      type: "hosts",
      filename: "newfile",
      resolver: "name"
    };
    component.onUpdateResolverData(newData);
    expect(component.newMachineResolver().data).toEqual(newData);
  });

  it("should save machineResolver", async () => {
    const panel = { close: () => {} } as any;
    jest.spyOn(panel, "close");
    machineResolverServiceMock.postMachineResolver.mockReturnValue(Promise.resolve(null));
    await component.saveMachineResolver(panel);
    expect(machineResolverServiceMock.postTestMachineResolver).toHaveBeenCalled();
    expect(machineResolverServiceMock.postMachineResolver).toHaveBeenCalled();
    expect(panel.close).toHaveBeenCalled();
  });

  it("should handle collapse and discard on confirm", async () => {
    const panel = { close: () => {}, open: () => {} } as any;
    jest.spyOn(panel, "close");
    jest.spyOn(panel, "open");
    component.newMachineResolver.set({ ...component.newMachineResolver(), resolvername: "test" });
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of("discard"));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component.handleCollapse(panel);
    await Promise.resolve();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(panel.close).toHaveBeenCalled();
  });

  it("should re-open panel when collapse dialog is cancelled", async () => {
    const panel = { close: jest.fn(), open: jest.fn() } as any;
    component.newMachineResolver.set({ ...component.newMachineResolver(), resolvername: "test" });
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of(null));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component.handleCollapse(panel);
    await Promise.resolve();
    expect(panel.open).toHaveBeenCalled();
    expect(panel.close).not.toHaveBeenCalled();
  });

  it("should save and exit when collapse dialog returns save-exit", async () => {
    const panel = { close: jest.fn(), open: jest.fn() } as any;
    component.dataValidatorSignal.set(() => true);
    component.newMachineResolver.set({ ...component.newMachineResolver(), resolvername: "test" });
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of("save-exit"));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    const saveSpy = jest.spyOn(component, "saveMachineResolver").mockResolvedValue(undefined);
    component.handleCollapse(panel);
    await Promise.resolve();
    expect(saveSpy).toHaveBeenCalledWith(panel);
  });

  it("should re-open panel on save-exit when canSave is false", async () => {
    const panel = { close: jest.fn(), open: jest.fn() } as any;
    component.dataValidatorSignal.set(() => false);
    component.newMachineResolver.set({ ...component.newMachineResolver(), resolvername: "test" });
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(of("save-exit"));
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    const saveSpy = jest.spyOn(component, "saveMachineResolver");
    component.handleCollapse(panel);
    await Promise.resolve();
    expect(panel.open).toHaveBeenCalled();
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it("should check if machineResolver can be saved", () => {
    component.dataValidatorSignal.set(() => true);
    component.newMachineResolver.set({ ...component.newMachineResolver(), resolvername: " " });
    expect(component.canSaveMachineResolver()).toBeFalsy();

    component.newMachineResolver.set({ ...component.newMachineResolver(), resolvername: "test" });
    expect(component.canSaveMachineResolver()).toBeTruthy();

    component.dataValidatorSignal.set(() => false);
    expect(component.canSaveMachineResolver()).toBeFalsy();
  });

  it("should reset machineResolver", () => {
    const data: LdapMachineResolverData = {
      type: "ldap",
      LDAPURI: "ldap://test",
      AUTHTYPE: "",
      TLS_VERIFY: false,
      START_TLS: false,
      TLS_CA_FILE: "",
      LDAPBASE: "",
      BINDDN: "",
      BINDPW: "",
      TIMEOUT: "",
      SIZELIMIT: "",
      SEARCHFILTER: "",
      IDATTRIBUTE: "",
      IPATTRIBUTE: "",
      HOSTNAMEATTRIBUTE: "",
      NOREFERRALS: "False",
      resolver: ""
    };
    component.newMachineResolver.set({
      resolvername: "test",
      type: "ldap",
      data: data
    });
    component.resetMachineResolver();
    expect(component.newMachineResolver()).toEqual(component.machineResolverDefault);
  });
});
