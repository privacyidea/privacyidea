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
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { MachineService } from "@services/machine/machine.service";
import { MachinesComponent } from "./machines.component";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMachineService, MockTableUtilsService } from "@testing/mock-services";

describe("MachinesComponent", () => {
  let component: MachinesComponent;
  let fixture: ComponentFixture<MachinesComponent>;
  let machineServiceMock: MockMachineService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MachinesComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: MachineService, useClass: MockMachineService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    machineServiceMock = TestBed.inject(MachineService) as unknown as MockMachineService;
    machineServiceMock.machines.set([
      { id: 1, hostname: ["host1"], ip: "1.1.1.1", resolver_name: "res1" },
      { id: 2, hostname: ["host2"], ip: "2.2.2.2", resolver_name: "res2" }
    ]);

    fixture = TestBed.createComponent(MachinesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display machines from service", () => {
    expect(component.machineDataSource().data.length).toBe(2);
    expect(component.machineDataSource().data[0].id).toBe(1);
  });

  it("should filter machines", () => {
    component.onFilterInput("host1");
    expect(component.machineDataSource().filter).toBe("host1");
  });

  it("should navigate to details page", () => {
    const router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    const machine = machineServiceMock.machines()[0];
    component.openDetailsDialog(machine);
    expect(router.navigateByUrl).toHaveBeenCalledWith(
      ROUTE_PATHS.CONFIGURATION_MACHINES_DETAILS + machine.id + "?resolver=" + encodeURIComponent(machine.resolver_name)
    );
  });

  it("should initialize paginator page size to the second page size option", () => {
    expect(component.paginator.pageSize).toBe(component.pageSizeOptions()[1]);
    expect(component.paginator.pageSize).toBe(10);
  });
});

describe("MachinesComponent pageSize fallback", () => {
  it("defaults pageSize to 10 when the second page size option is missing", async () => {
    await TestBed.configureTestingModule({
      imports: [MachinesComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: MachineService, useClass: MockMachineService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    const tableUtils = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
    tableUtils.pageSizeOptions.set([5]);

    const component = TestBed.createComponent(MachinesComponent).componentInstance;

    expect(component.pageSizeOptions()[1]).toBeUndefined();
    expect(component.pageSize()).toBe(10);
  });
});
