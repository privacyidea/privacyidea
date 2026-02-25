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
import { MachinesComponent } from "./machines.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { MachineService } from "../../../services/machine/machine.service";
import { signal } from "@angular/core";

describe("MachinesComponent", () => {
  let component: MachinesComponent;
  let fixture: ComponentFixture<MachinesComponent>;
  let machineServiceMock: any;

  beforeEach(async () => {
    machineServiceMock = {
      machines: signal([
        { id: 1, hostname: ["host1"], ip: "1.1.1.1", resolver_name: "res1" },
        { id: 2, hostname: ["host2"], ip: "2.2.2.2", resolver_name: "res2" }
      ])
    };

    await TestBed.configureTestingModule({
      imports: [MachinesComponent, NoopAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineService, useValue: machineServiceMock }
      ]
    }).overrideComponent(MachinesComponent, {
      set: {
        providers: [
          { provide: MatDialog, useValue: { open: jest.fn() } }
        ]
      }
    }).compileComponents();

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

  it("should open details dialog", () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const machine = machineServiceMock.machines()[0];
    component.openDetailsDialog(machine);
    expect(dialog.open).toHaveBeenCalled();
  });
});
