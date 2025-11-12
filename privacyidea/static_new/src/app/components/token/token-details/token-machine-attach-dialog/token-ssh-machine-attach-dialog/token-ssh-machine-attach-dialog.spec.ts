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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { Observable, of } from "rxjs";

import { TokenSshMachineAssignDialogComponent } from "./token-ssh-machine-attach-dialog";

import { ApplicationService } from "../../../../../services/application/application.service";
import { MachineService } from "../../../../../services/machine/machine.service";
import { UserService } from "../../../../../services/user/user.service";
import { MockApplicationService, MockMachineService, MockUserService } from "../../../../../../testing/mock-services";
import "@angular/localize/init";

type TestMachine = {
  id: number;
  hostname: string[];
  ip: string;
  resolver_name: string;
};

describe("TokenSshMachineAssignDialogComponent", () => {
  let component: TokenSshMachineAssignDialogComponent;
  let fixture: ComponentFixture<TokenSshMachineAssignDialogComponent>;
  let dialogRef: { close: jest.Mock };
  let appSvc: MockApplicationService;
  let machSvc: MockMachineService;
  let userSvc: MockUserService;

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    appSvc = new MockApplicationService();
    machSvc = new MockMachineService();
    userSvc = new MockUserService();

    await TestBed.configureTestingModule({
      imports: [TokenSshMachineAssignDialogComponent, BrowserAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: { tokenSerial: "SER-SSH", tokenDetails: {}, tokenType: "ssh" } },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: ApplicationService, useValue: appSvc },
        { provide: MachineService, useValue: machSvc },
        { provide: UserService, useValue: userSvc }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenSshMachineAssignDialogComponent);
    component = fixture.componentInstance;

    machSvc.machines.set([
      { id: 1, hostname: ["host-1"], ip: "10.0.0.1", resolver_name: "resA" },
      { id: 2, hostname: ["host-2", "alias-2"], ip: "10.0.0.2", resolver_name: "resB" }
    ] as any);

    userSvc.users.set([{ username: "alice" }, { username: "bob" }, { username: "carol" }] as any);

    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("availableApplications includes 'ssh' when service IDs are available", () => {
    expect(component.availableApplications()).toEqual(["ssh"]);
  });

  it("availableServiceIds mirrors application service IDs", () => {
    expect(component.availableServiceIds()).toEqual(["svc-1", "svc-2"]);

    appSvc.applications.set({
      ssh: { options: { sshkey: { service_id: { value: [] } } } }
    } as any);
    expect(component.availableApplications()).toEqual([]);
    expect(component.availableServiceIds()).toEqual([]);
  });

  it("availableUsers maps usernames from user service", () => {
    expect(component.availableUsers()).toEqual(["alice", "bob", "carol"]);
  });

  it("filteredMachines respects machineFilter via selectedMachine valueChanges", () => {
    component.ngOnInit();

    expect(component.filteredMachines()).toHaveLength(2);

    component.selectedMachine.setValue("host-2");
    expect(component.filteredMachines()).toHaveLength(1);
    const only = component.filteredMachines()![0] as any;
    expect(only.hostname).toEqual(["host-2", "alias-2"]);
  });

  it("filteredUsers respects userFilter via selectedUser valueChanges (subscription wired in ngOnInit)", () => {
    component.ngOnInit();
    component.selectedMachine.setValue("anything");

    component.selectedUser.setValue("bo");
    expect(component.filteredUsers()).toEqual(["bob"]);

    component.selectedUser.setValue("");
    expect(component.filteredUsers()).toEqual(["alice", "bob", "carol"]);
  });

  it("getFullMachineName formats correctly", () => {
    const m: TestMachine = { id: 7, hostname: ["a", "b"], ip: "1.2.3.4", resolver_name: "R" };
    expect(component.getFullMachineName(m)).toBe("a, b [7] (1.2.3.4 in R)");
    expect(component.getFullMachineName("literal")).toBe("literal");
  });

  it("onAssign: does nothing if form invalid", () => {
    component.selectedMachine.setValue("");
    component.selectedServiceId.setValue("");
    component.selectedUser.setValue("");

    const postSpy = jest.spyOn(machSvc, "postAssignMachineToToken");

    component.onAssign();

    expect(postSpy).not.toHaveBeenCalled();
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it("onAssign: aborts if selectedMachine is a string", () => {
    component.selectedMachine.setValue("just-a-string");
    component.selectedServiceId.setValue("svc-1");
    component.selectedUser.setValue("alice");

    const postSpy = jest.spyOn(machSvc, "postAssignMachineToToken");

    component.onAssign();

    expect(postSpy).not.toHaveBeenCalled();
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it("onAssign: posts payload, reloads resources (via subscription), and closes with the same Observable", () => {
    const machine: TestMachine = { id: 2, hostname: ["host-2"], ip: "10.0.0.2", resolver_name: "resB" } as any;

    component.selectedMachine.setValue(machine);
    component.selectedServiceId.setValue("svc-2");
    component.selectedUser.setValue("bob");

    const postSpy = jest.spyOn(machSvc, "postAssignMachineToToken").mockReturnValue(of({}) as any);

    component.onAssign();

    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(postSpy).toHaveBeenCalledWith({
      service_id: "svc-2",
      user: "bob",
      serial: "SER-SSH",
      application: "ssh",
      machineid: 2,
      resolver: "resB"
    });

    expect(machSvc.machinesResource.reload).toHaveBeenCalled();
    expect(machSvc.tokenApplicationResource.reload).toHaveBeenCalled();

    const returned$ = postSpy.mock.results[0].value as Observable<any>;
    expect(dialogRef.close).toHaveBeenCalledWith(returned$);
  });

  it("onCancel closes with null", () => {
    component.onCancel();
    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });

  describe("machineValidator", () => {
    it("returns {required:true} when value is falsy or string", () => {
      expect(component.machineValidator({ value: null } as any)).toEqual({ required: true });
      expect(component.machineValidator({ value: "" } as any)).toEqual({ required: true });
      expect(component.machineValidator({ value: "str" } as any)).toEqual({ required: true });
    });

    it("returns {invalidMachine:true} when object is missing fields", () => {
      expect(component.machineValidator({ value: { id: 1, hostname: ["h"], ip: "x" } } as any)).toEqual({
        invalidMachine: true
      });
    });

    it("returns null for a valid machine", () => {
      expect(
        component.machineValidator({
          value: { id: 1, hostname: ["h"], ip: "x", resolver_name: "R" }
        } as any)
      ).toBeNull();
    });
  });
});
