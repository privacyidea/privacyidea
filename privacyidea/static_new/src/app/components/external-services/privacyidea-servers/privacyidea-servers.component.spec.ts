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
import { PrivacyideaServersComponent } from "./privacyidea-servers.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { PrivacyideaServerService } from "../../../services/privacyidea-server/privacyidea-server.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { signal } from "@angular/core";

describe("PrivacyideaServersComponent", () => {
  let component: PrivacyideaServersComponent;
  let fixture: ComponentFixture<PrivacyideaServersComponent>;
  let privacyideaServerServiceMock: any;
  let dialogServiceMock: any;
  let dialog: MatDialog;

  beforeEach(async () => {
    privacyideaServerServiceMock = {
      privacyideaServers: signal([
        { identifier: "server1", url: "http://s1", tls: true, description: "desc1" },
        { identifier: "server2", url: "http://s2", tls: false, description: "desc2" },
      ]),
      deletePrivacyideaServer: jest.fn(),
    };

    dialogServiceMock = {
      confirm: jest.fn().mockResolvedValue(true),
    };

    await TestBed.configureTestingModule({
      imports: [PrivacyideaServersComponent, NoopAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PrivacyideaServerService, useValue: privacyideaServerServiceMock },
        { provide: DialogService, useValue: dialogServiceMock },
      ]
    }).overrideComponent(PrivacyideaServersComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: { open: jest.fn() } }
        ]
      }
    }).compileComponents();

    fixture = TestBed.createComponent(PrivacyideaServersComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display servers from service", () => {
    expect(component.privacyideaDataSource().data.length).toBe(2);
    expect(component.privacyideaDataSource().data[0].identifier).toBe("server1");
  });

  it("should filter servers", () => {
    component.onFilterInput("server1");
    expect(component.privacyideaDataSource().filter).toBe("server1");
  });

  it("should reset filter", () => {
    component.onFilterInput("someFilter");
    component.resetFilter();
    expect(component.filterString()).toBe("");
    expect(component.privacyideaDataSource().filter).toBe("");
  });

  it("should open edit dialog", () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const server = privacyideaServerServiceMock.privacyideaServers()[0];
    component.openEditDialog(server);
    expect(dialog.open).toHaveBeenCalled();
  });

  it("should delete server after confirmation", async () => {
    const server = privacyideaServerServiceMock.privacyideaServers()[0];
    component.deleteServer(server);
    expect(dialogServiceMock.confirm).toHaveBeenCalled();
    // Wait for the microtask queue to empty because of the .then() in deleteServer
    await Promise.resolve();
    expect(privacyideaServerServiceMock.deletePrivacyideaServer).toHaveBeenCalledWith("server1");
  });
});
