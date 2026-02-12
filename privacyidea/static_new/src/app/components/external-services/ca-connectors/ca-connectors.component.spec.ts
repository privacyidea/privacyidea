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
import { CaConnectorsComponent } from "./ca-connectors.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { CaConnectorService } from "../../../services/ca-connector/ca-connector.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { signal } from "@angular/core";
import { MockDialogService } from "src/testing/mock-services";
import { Subject } from "rxjs";
import { MockMatDialogRef } from "src/testing/mock-mat-dialog-ref";

describe("CaConnectorsComponent", () => {
  let component: CaConnectorsComponent;
  let fixture: ComponentFixture<CaConnectorsComponent>;
  let caConnectorServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  beforeEach(async () => {
    caConnectorServiceMock = {
      caConnectors: signal([
        { connectorname: "conn1", type: "local" },
        { connectorname: "conn2", type: "microsoft" }
      ]),
      deleteCaConnector: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [CaConnectorsComponent, NoopAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: CaConnectorService, useValue: caConnectorServiceMock },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .overrideComponent(CaConnectorsComponent, {
        add: {
          providers: [{ provide: MatDialog, useValue: { open: jest.fn() } }]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(CaConnectorsComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
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

  it("should open edit dialog", () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const connector = caConnectorServiceMock.caConnectors()[0];
    component.openEditDialog(connector);
    expect(dialog.open).toHaveBeenCalled();
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
