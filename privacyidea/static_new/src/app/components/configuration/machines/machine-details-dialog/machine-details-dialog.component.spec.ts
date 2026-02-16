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
import { MachineDetailsDialogComponent } from "./machine-details-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { MachineService } from "../../../../services/machine/machine.service";
import { ApplicationService } from "../../../../services/application/application.service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { of } from "rxjs";
import { signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContentService } from "../../../../services/content/content.service";
import { ROUTE_PATHS } from "../../../../route_paths";

describe("MachineDetailsDialogComponent", () => {
  let component: MachineDetailsDialogComponent;
  let fixture: ComponentFixture<MachineDetailsDialogComponent>;
  let machineServiceMock: any;
  let applicationServiceMock: any;
  let dialogServiceMock: any;
  let matDialogRefMock: any;
  let contentServiceMock: any;

  const mockMachine = { id: 1, hostname: ["host1"], ip: "1.1.1.1", resolver_name: "res1" };

  beforeEach(async () => {
    machineServiceMock = {
      getMachineTokens: jest.fn().mockReturnValue(of({
        result: {
          value: [{
            id: 10,
            serial: "S1",
            application: "ssh",
            type: "sshkey",
            options: {}
          }]
        }
      })),
      deleteTokenMtid: jest.fn().mockReturnValue(of({})),
      postAssignMachineToToken: jest.fn().mockReturnValue(of({}))
    };

    applicationServiceMock = {
      applications: signal({
        ssh: { options: {} },
        offline: { options: {} },
        luks: { options: {} }
      })
    };

    dialogServiceMock = {
      confirm: jest.fn().mockResolvedValue(true)
    };

    matDialogRefMock = {
      close: jest.fn(),
      backdropClick: jest.fn().mockReturnValue(of({})),
      keydownEvents: jest.fn().mockReturnValue(of({}))
    };

    contentServiceMock = {
      routeUrl: signal(ROUTE_PATHS.CONFIGURATION_MACHINES),
      tokenSelected: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [MachineDetailsDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: mockMachine },
        { provide: MatDialogRef, useValue: matDialogRefMock },
        { provide: MachineService, useValue: machineServiceMock },
        { provide: ApplicationService, useValue: applicationServiceMock },
        { provide: DialogService, useValue: dialogServiceMock },
        { provide: ContentService, useValue: contentServiceMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineDetailsDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should load tokens on init", () => {
    expect(machineServiceMock.getMachineTokens).toHaveBeenCalledWith({ machineid: 1, resolver: "res1" });
    expect(component.dataSource.data.length).toBe(1);
    expect(component.dataSource.data[0].serial).toBe("S1");
  });

  it("should detach token after confirmation", async () => {
    const token = component.dataSource.data[0];
    component.detachToken(token);
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    await Promise.resolve();
    expect(machineServiceMock.deleteTokenMtid).toHaveBeenCalledWith("S1", "ssh", "10");
  });

  it("should attach token", () => {
    component.newTokenSerial = "S2";
    component.selectedApplication = "ssh";
    component.attachToken();
    expect(machineServiceMock.postAssignMachineToToken).toHaveBeenCalledWith({
      serial: "S2",
      application: "ssh",
      machineid: 1,
      resolver: "res1"
    });
  });

  it("should close dialog", () => {
    component.close();
    expect(matDialogRefMock.close).toHaveBeenCalled();
  });

  it("should navigate and close when token is clicked", () => {
    component.onTokenClick("S1");
    expect(contentServiceMock.tokenSelected).toHaveBeenCalledWith("S1");
    expect(matDialogRefMock.close).toHaveBeenCalled();
  });
});
