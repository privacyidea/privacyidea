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
import { MachineService } from "../../../../services/machine/machine.service";
import { ApplicationService } from "../../../../services/application/application.service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { of } from "rxjs";
import { SimpleConfirmationDialogComponent } from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { computed, signal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContentService } from "../../../../services/content/content.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { TokenService } from "../../../../services/token/token.service";
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";

describe("MachineDetailsDialogComponent", () => {
  let component: MachineDetailsDialogComponent;
  let fixture: ComponentFixture<MachineDetailsDialogComponent>;
  let machineServiceMock: any;
  let applicationServiceMock: any;
  let dialogServiceMock: any;
  let routerMock: any;
  let contentServiceMock: any;
  let tokenServiceMock: any;

  const mockMachine = { id: 1, hostname: ["host1"], ip: "1.1.1.1", resolver_name: "res1" };

  beforeEach(async () => {
    // Inject machine data via history state (the way the component reads it)
    window.history.pushState({ machine: mockMachine }, "");

    machineServiceMock = {
      getMachineTokens: jest.fn().mockReturnValue(of({
        result: {
          value: [{
            id: 10,
            serial: "S1",
            application: "ssh",
            type: "sshkey",
            hostname: "host1",
            options: { user: "alice", service_id: "svc1" }
          }]
        }
      })),
      machines: signal([mockMachine]),
      deleteTokenById: jest.fn().mockReturnValue(of({})),
      postAssignMachineToToken: jest.fn().mockReturnValue(of({})),
      postTokenOption: jest.fn().mockReturnValue(of({}))
    };

    applicationServiceMock = {
      applications: signal({
        ssh: { options: {} },
        offline: { options: {} },
        luks: { options: {} }
      })
    };

    dialogServiceMock = {
      openDialog: jest.fn().mockReturnValue({
        afterClosed: jest.fn().mockReturnValue(of(true))
      })
    };

    routerMock = {
      navigateByUrl: jest.fn()
    };

    tokenServiceMock = {
      selectedToken: signal(null),
      tokenOptions: signal([]),
      filteredTokenOptions: computed(() => []),
      getTokenDetails: jest.fn().mockReturnValue(of({ result: { value: { tokens: [] } } }))
    };

    contentServiceMock = {
      routeUrl: signal(ROUTE_PATHS.CONFIGURATION_MACHINES),
      tokenSelected: jest.fn(),
      machineResolverSelected: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [MachineDetailsDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MachineService, useValue: machineServiceMock },
        { provide: ApplicationService, useValue: applicationServiceMock },
        { provide: DialogService, useValue: dialogServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: Router, useValue: routerMock },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: convertToParamMap({ id: "1" }),
              queryParamMap: convertToParamMap({ resolver: "res1" })
            }
          }
        }
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
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(expect.objectContaining({
      component: SimpleConfirmationDialogComponent
    }));
    await Promise.resolve();
    expect(machineServiceMock.deleteTokenById).toHaveBeenCalledWith("S1", "ssh", "10");
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

  it("should save edited options", () => {
    const token = component.dataSource.data[0];
    component.startEdit(token);
    component.editedOptions[token.id] = { user: "bob", service_id: "svc2" };
    component.saveOptions(token);
    const machine = component.data();
    expect(machineServiceMock.postTokenOption).toHaveBeenCalledWith(
      token.hostname,
      String(machine!.id),
      machine!.resolver_name,
      token.serial,
      token.application,
      String(token.id),
      { user: "bob", service_id: "svc2" }
    );
  });

  it("should call tokenSelected when token is clicked", () => {
    component.onTokenClick("S1");
    expect(contentServiceMock.tokenSelected).toHaveBeenCalledWith("S1");
  });

  it("should call machineResolverSelected when machine resolver is clicked", () => {
    component.onMachineResolverClick("res1");
    expect(contentServiceMock.machineResolverSelected).toHaveBeenCalledWith("res1");
  });
});
