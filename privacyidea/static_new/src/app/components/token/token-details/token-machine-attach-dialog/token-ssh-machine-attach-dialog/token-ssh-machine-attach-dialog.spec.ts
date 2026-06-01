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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import { Observable, of } from "rxjs";

import { TokenSshMachineAssignDialogComponent } from "./token-ssh-machine-attach-dialog";

import { ApplicationService } from "@services/application/application.service";
import { MachineService } from "@services/machine/machine.service";
import { UserService } from "@services/user/user.service";
import { MockApplicationService, MockMachineService, MockUserService } from "@testing/mock-services";

interface TestMachine {
  id: number;
  hostname: string[];
  ip: string;
  resolver_name: string;
}

describe("TokenSshMachineAssignDialogComponent", () => {
  let component: TokenSshMachineAssignDialogComponent;
  let fixture: ComponentFixture<TokenSshMachineAssignDialogComponent>;
  let dialogRef: { close: jest.Mock };
  let applicationService: MockApplicationService;
  let machineService: MockMachineService;
  let userService: MockUserService;

  beforeEach(async () => {
    dialogRef = { close: jest.fn() };
    applicationService = new MockApplicationService();
    machineService = new MockMachineService();
    userService = new MockUserService();

    await TestBed.configureTestingModule({
      imports: [TokenSshMachineAssignDialogComponent, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: { tokenSerial: "SER-SSH", tokenDetails: {}, tokenType: "ssh" } },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: ApplicationService, useValue: applicationService },
        { provide: MachineService, useValue: machineService },
        { provide: UserService, useValue: userService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenSshMachineAssignDialogComponent);
    component = fixture.componentInstance;

    machineService.machines.set([
      { id: 1, hostname: ["host-1"], ip: "10.0.0.1", resolver_name: "resA" },
      { id: 2, hostname: ["host-2", "alias-2"], ip: "10.0.0.2", resolver_name: "resB" }
    ] as any);

    userService.users.set([{ username: "alice" }, { username: "bob" }, { username: "carol" }] as any);

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

    applicationService.applications.set({
      ssh: { options: { sshkey: { service_id: { value: [] } } } }
    } as any);
    expect(component.availableApplications()).toEqual([]);
    expect(component.availableServiceIds()).toEqual([]);
  });

  it("availableUsers maps usernames from user service", () => {
    expect(component.availableUsers()).toEqual(["alice", "bob", "carol"]);
  });

  it("filteredMachines respects machineFilter via selectedMachineValue effect", () => {
    expect(component.filteredMachines()).toHaveLength(2);

    component.selectedMachineValue.set("host-2");
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();
    expect(component.filteredMachines()).toHaveLength(1);
    const only = component.filteredMachines()![0] as any;
    expect(only.hostname).toEqual(["host-2", "alias-2"]);
  });

  it("filteredUsers respects userFilter via selectedUserValue effect", () => {
    component.selectedUserValue.set("bo");
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();
    expect(component.filteredUsers()).toEqual(["bob"]);

    component.selectedUserValue.set("");
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();
    expect(component.filteredUsers()).toEqual(["alice", "bob", "carol"]);
  });

  it("getFullMachineName formats correctly", () => {
    const m: TestMachine = { id: 7, hostname: ["a", "b"], ip: "1.2.3.4", resolver_name: "R" };
    expect(component.getFullMachineName(m)).toBe("a, b [7] (1.2.3.4 in R)");
    expect(component.getFullMachineName("literal")).toBe("literal");
  });

  it("onAssign: does nothing if form invalid", () => {
    component.selectedMachineValue.set("");
    component.selectedServiceIdValue.set("");
    component.selectedUserValue.set("");

    const postSpy = jest.spyOn(machineService, "postAssignMachineToToken");

    component.onAssign();

    expect(postSpy).not.toHaveBeenCalled();
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it("onAssign: aborts if selectedMachine is a string", () => {
    component.selectedMachineValue.set("just-a-string");
    component.selectedServiceIdValue.set("svc-1");
    component.selectedUserValue.set("alice");

    const postSpy = jest.spyOn(machineService, "postAssignMachineToToken");

    component.onAssign();

    expect(postSpy).not.toHaveBeenCalled();
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it("onAssign: posts payload, reloads resources (via subscription), and closes with the same Observable", () => {
    const machine: TestMachine = { id: 2, hostname: ["host-2"], ip: "10.0.0.2", resolver_name: "resB" } as any;

    component.selectedMachineValue.set(machine);
    component.selectedServiceIdValue.set("svc-2");
    component.selectedUserValue.set("bob");

    const postSpy = jest.spyOn(machineService, "postAssignMachineToToken").mockReturnValue(of({}) as any);

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

    expect(machineService.machinesResource.reload).toHaveBeenCalled();
    expect(machineService.tokenApplicationResource.reload).toHaveBeenCalled();

    const returned$ = postSpy.mock.results[0].value as Observable<any>;
    expect(dialogRef.close).toHaveBeenCalledWith(returned$);
  });

  it("onCancel closes with null", () => {
    component.onCancel();
    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });

  describe("selectedMachineForm validation", () => {
    it("is invalid when value is falsy or a plain string", () => {
      component.selectedMachineValue.set("");
      expect(component.selectedMachineForm().valid()).toBe(false);
      expect(
        component
          .selectedMachineForm()
          .errors()
          .some((e) => e.kind === "required")
      ).toBe(true);

      component.selectedMachineValue.set("str");
      expect(component.selectedMachineForm().valid()).toBe(false);
      expect(
        component
          .selectedMachineForm()
          .errors()
          .some((e) => e.kind === "required")
      ).toBe(true);
    });

    it("reports invalidMachine when object is missing required fields", () => {
      component.selectedMachineValue.set({ id: 1, hostname: ["h"], ip: "x" } as any);
      expect(component.selectedMachineForm().valid()).toBe(false);
      expect(
        component
          .selectedMachineForm()
          .errors()
          .some((e) => e.kind === "invalidMachine")
      ).toBe(true);
    });

    it("is valid for a complete machine object", () => {
      component.selectedMachineValue.set({
        id: 1,
        hostname: ["h"],
        ip: "x",
        resolver_name: "R"
      } as any);
      expect(component.selectedMachineForm().valid()).toBe(true);
    });
  });
});
