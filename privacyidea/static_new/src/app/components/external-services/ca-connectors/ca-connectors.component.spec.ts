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
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideRouter, Router } from "@angular/router";
import { Subject } from "rxjs";
import { MockMatDialogRef } from "../../../../testing/mock-mat-dialog-ref";
import { MockDialogService } from "../../../../testing/mock-services";
import { CaConnectorService } from "../../../services/ca-connector/ca-connector.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { ROUTE_PATHS } from "../../../route_paths";
import { CaConnectorsComponent } from "./ca-connectors.component";

describe("CaConnectorsComponent", () => {
  let component: CaConnectorsComponent;
  let fixture: ComponentFixture<CaConnectorsComponent>;
  let caConnectorServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  beforeEach(async () => {
    caConnectorServiceMock = {
      caConnectors: signal([
        { connectorname: "conn1", type: "local" },
        { connectorname: "conn2", type: "microsoft" }
      ]),
      deleteCaConnector: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [CaConnectorsComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: CaConnectorService, useValue: caConnectorServiceMock },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(CaConnectorsComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    confirmClosed = new Subject();
    let dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display connectors from service", () => {
    expect(component.caConnectorDataSource().data.length).toBe(2);
    expect(component.caConnectorDataSource().data[0].connectorname).toBe("conn1");
  });

  it("should filter connectors", () => {
    component.onFilterInput("conn1");
    expect(component.caConnectorDataSource().filter).toBe("conn1");
  });

  it("should navigate to new connector route on openEditDialog without connector", () => {
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.openEditDialog();
    expect(spy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_NEW);
  });

  it("should navigate to details route on openEditDialog with connector", () => {
    const spy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    const connector = caConnectorServiceMock.caConnectors()[0];
    component.openEditDialog(connector);
    expect(spy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_DETAILS + connector.connectorname);
  });

  it("should delete connector after confirmation", () => {
    const connector = caConnectorServiceMock.caConnectors()[0];
    component.deleteConnector(connector);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();

    expect(caConnectorServiceMock.deleteCaConnector).toHaveBeenCalledWith("conn1");
  });
});
