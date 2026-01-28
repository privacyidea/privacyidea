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
import { RadiusServersComponent } from "./radius-servers.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { RadiusService } from "../../../services/radius/radius.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { signal } from "@angular/core";

describe("RadiusServersComponent", () => {
  let component: RadiusServersComponent;
  let fixture: ComponentFixture<RadiusServersComponent>;
  let radiusServiceMock: any;
  let dialogServiceMock: any;

  beforeEach(async () => {
    radiusServiceMock = {
      radiusServers: signal([
        { identifier: "server1", server: "1.1.1.1" },
        { identifier: "server2", server: "2.2.2.2" }
      ]),
      deleteRadiusServer: jest.fn()
    };

    dialogServiceMock = {
      confirm: jest.fn().mockResolvedValue(true)
    };

    await TestBed.configureTestingModule({
      imports: [RadiusServersComponent, NoopAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: RadiusService, useValue: radiusServiceMock },
        { provide: DialogService, useValue: dialogServiceMock }
      ]
    }).overrideComponent(RadiusServersComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: { open: jest.fn() } }
        ]
      }
    }).compileComponents();

    fixture = TestBed.createComponent(RadiusServersComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display servers from service", () => {
    expect(component.radiusDataSource().data.length).toBe(2);
    expect(component.radiusDataSource().data[0].identifier).toBe("server1");
  });

  it("should filter servers", () => {
    component.onFilterInput("server1");
    expect(component.radiusDataSource().filter).toBe("server1");
  });

  it("should open edit dialog", () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const server = radiusServiceMock.radiusServers()[0];
    component.openEditDialog(server);
    expect(dialog.open).toHaveBeenCalled();
  });

  it("should delete server after confirmation", async () => {
    const server = radiusServiceMock.radiusServers()[0];

    component.deleteServer(server);

    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    await Promise.resolve();
    expect(radiusServiceMock.deleteRadiusServer).toHaveBeenCalledWith("server1");
  });
});
