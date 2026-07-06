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
import { Router, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PrivacyideaServer, PrivacyideaServerService } from "@services/privacyidea-server/privacyidea-server.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockAuthService,
  MockDialogService,
  MockPrivacyideaServerService,
  MockTableUtilsService
} from "@testing/mock-services";
import { Subject } from "rxjs";
import { PrivacyideaServersComponent } from "./privacyidea-servers.component";

describe("PrivacyideaServersComponent", () => {
  let component: PrivacyideaServersComponent;
  let fixture: ComponentFixture<PrivacyideaServersComponent>;
  let privacyideaServerServiceMock: MockPrivacyideaServerService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PrivacyideaServersComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: PrivacyideaServerService, useClass: MockPrivacyideaServerService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    privacyideaServerServiceMock = TestBed.inject(
      PrivacyideaServerService
    ) as unknown as MockPrivacyideaServerService;
    privacyideaServerServiceMock.remoteServerOptions.set([
      { identifier: "server1", url: "http://s1", tls: true, description: "desc1" },
      { identifier: "server2", url: "http://s2", tls: false, description: "desc2" }
    ] as unknown as PrivacyideaServer[]);

    fixture = TestBed.createComponent(PrivacyideaServersComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
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

  it("should navigate to new server route on openEditDialog without server", () => {
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.openEditDialog();
    expect(spy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA_NEW);
  });

  it("should navigate to details route on openEditDialog with server", () => {
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    const server = privacyideaServerServiceMock.remoteServerOptions()[0];
    component.openEditDialog(server);
    expect(spy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA_DETAILS + server.identifier);
  });

  it("should delete server after confirmation", () => {
    const server = privacyideaServerServiceMock.remoteServerOptions()[0];
    component.deleteServer(server);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();

    expect(privacyideaServerServiceMock.deletePrivacyideaServer).toHaveBeenCalledWith("server1");
  });
});
