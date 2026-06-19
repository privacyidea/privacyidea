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
import { MatDialog } from "@angular/material/dialog";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { MachineResolver, MachineResolverService } from "@services/machine-resolver/machine-resolver.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockMachineResolverService } from "@testing/mock-services/mock-machine-resolver-service";
import { of } from "rxjs";
import { MachineResolverComponent } from "./machine-resolver.component";

class LocalMockMatDialog {
  result$ = of(true);
  open = jest.fn().mockReturnValue({
    afterClosed: () => this.result$
  });
}

describe("MachineResolverComponent", () => {
  let component: MachineResolverComponent;
  let fixture: ComponentFixture<MachineResolverComponent>;
  let machineResolverServiceMock: MockMachineResolverService;
  let authServiceMock: MockAuthService;
  let dialog: LocalMockMatDialog;
  let router: Router;

  beforeEach(async () => {
    dialog = new LocalMockMatDialog();
    await TestBed.configureTestingModule({
      imports: [MachineResolverComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineResolverService, useClass: MockMachineResolverService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: MatDialog, useValue: dialog },
        {
          provide: Router,
          useValue: { navigate: jest.fn(), navigateByUrl: jest.fn(), events: of(), url: "" }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineResolverComponent);
    component = fixture.componentInstance;
    machineResolverServiceMock = TestBed.inject(MachineResolverService) as unknown as MockMachineResolverService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    router = TestBed.inject(Router);
    authServiceMock.actionAllowed.mockReturnValue(true);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have name and type columns defined", () => {
    expect(component.columnKeys).toEqual(["resolvername", "type"]);
  });

  it("should filter machine resolvers by name or type", () => {
    const resolvers = [
      { resolvername: "hosts1", type: "hosts", data: { resolver: "hosts1", type: "hosts" } },
      { resolvername: "ldap1", type: "ldap", data: { resolver: "ldap1", type: "ldap" } }
    ] as MachineResolver[];
    machineResolverServiceMock.machineResolvers.set(resolvers);
    fixture.detectChanges();

    const ds = component.machineResolversDataSource();
    expect(ds.filterPredicate(resolvers[0], "hosts1")).toBeTruthy();
    expect(ds.filterPredicate(resolvers[1], "ldap")).toBeTruthy();
    expect(ds.filterPredicate(resolvers[0], "nomatch")).toBeFalsy();
    expect(ds.filterPredicate(resolvers[0], "  ")).toBeTruthy();

    component.onFilterInput("ldap1");
    expect(component.machineResolversDataSource().filteredData.length).toBe(1);
    component.resetFilter();
    expect(component.filterString()).toBe("");
    expect(component.machineResolversDataSource().filteredData.length).toBe(2);
  });

  it("onNewMachineResolver navigates to the new page", () => {
    component.onNewMachineResolver();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER_NEW);
  });

  it("onEditMachineResolver navigates to the details page", () => {
    component.onEditMachineResolver({ resolvername: "hosts1" } as MachineResolver);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.MACHINE_RESOLVER_DETAILS + "hosts1");
  });

  it("onDeleteMachineResolver deletes after confirmation", async () => {
    dialog.result$ = of(true);
    await component.onDeleteMachineResolver({ resolvername: "hosts1" } as MachineResolver);
    expect(machineResolverServiceMock.deleteMachineResolver).toHaveBeenCalledWith("hosts1");
  });

  it("onDeleteMachineResolver does not delete when cancelled", async () => {
    dialog.result$ = of(false);
    await component.onDeleteMachineResolver({ resolvername: "hosts1" } as MachineResolver);
    expect(machineResolverServiceMock.deleteMachineResolver).not.toHaveBeenCalled();
  });
});
