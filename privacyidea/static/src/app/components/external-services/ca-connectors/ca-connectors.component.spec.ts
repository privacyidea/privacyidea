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
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { TableAction } from "@components/shared/table-actions/table-actions.component";
import { Router, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { CaConnectorService } from "@services/ca-connector/ca-connector.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { expectsTableStateGating } from "@testing/table-state-gating";
import {
  MockAuthService,
  MockCaConnectorService,
  MockDialogService,
  MockTableUtilsService
} from "@testing/mock-services";
import { Subject } from "rxjs";
import { CaConnectorsComponent } from "./ca-connectors.component";

describe("CaConnectorsComponent", () => {
  let component: CaConnectorsComponent;
  let fixture: ComponentFixture<CaConnectorsComponent>;
  let caConnectorServiceMock: MockCaConnectorService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CaConnectorsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: CaConnectorService, useClass: MockCaConnectorService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    caConnectorServiceMock = TestBed.inject(CaConnectorService) as unknown as MockCaConnectorService;
    caConnectorServiceMock.caConnectors.set([
      { connectorname: "conn1", type: "local", data: {} },
      { connectorname: "conn2", type: "microsoft", data: {} }
    ]);

    fixture = TestBed.createComponent(CaConnectorsComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "caconnectorread"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should only select the connectors left by the filter", async () => {
    component.onFilterInput("conn1");
    fixture.detectChanges();
    await fixture.whenStable();

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((row) => row.connectorname)).toEqual(["conn1"]);
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
    component.selector.selectRow(connector);
    component.deleteSelected();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();

    expect(caConnectorServiceMock.deleteCaConnector).toHaveBeenCalledWith("conn1");
  });

  describe("toolbar actions", () => {
    const toolbarAction = (id: string): TableAction => {
      const found = component["toolbarActions"]().find((candidate) => candidate.id === id);
      if (!found) {
        throw new Error(`no toolbar action ${id}`);
      }
      return found;
    };
    const toolbarButton = (label: string): HTMLButtonElement | undefined =>
      Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll("app-table-actions button")).find(
        (button) => button.textContent?.includes(label)
      );
    const setRights = (rights: string[]) => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
      fixture.detectChanges();
    };

    it("offers create and delete in that order", () => {
      expect(component["toolbarActions"]().map((action) => action.id)).toEqual(["create", "delete"]);
      expect(toolbarAction("create").label).toBe("Create CA Connector");
      expect(toolbarAction("delete").label).toBe("Delete");
    });

    it("shows both actions while the read right is granted", () => {
      setRights(["caconnectorread"]);

      expect(component["toolbarActions"]().every((action) => action.visible !== false)).toBe(true);
      expect(toolbarButton("Create CA Connector")).toBeTruthy();
      expect(toolbarButton("Delete")).toBeTruthy();
    });

    it("draws no toolbar while the read right is denied", () => {
      setRights([]);

      expect(fixture.nativeElement.querySelector("app-table-actions")).toBeNull();
      expect(toolbarButton("Create CA Connector")).toBeUndefined();
    });

    it("keeps create enabled and disables delete until a row is selected", () => {
      setRights(["caconnectorread"]);

      expect(toolbarAction("create").disabled).toBeFalsy();
      expect(toolbarAction("delete").disabled).toBe(true);
      expect(toolbarButton("Create CA Connector")?.disabled).toBe(false);
      expect(toolbarButton("Delete")?.disabled).toBe(true);

      component.selector.selectRow(caConnectorServiceMock.caConnectors()[0]);
      fixture.detectChanges();

      expect(toolbarAction("create").disabled).toBeFalsy();
      expect(toolbarAction("delete").disabled).toBe(false);
      expect(toolbarButton("Delete")?.disabled).toBe(false);
    });

    it("runs create by opening the new-entry route", () => {
      const navigate = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
      navigate.mockClear();

      toolbarAction("create").run?.();

      expect(navigate).toHaveBeenCalledTimes(1);
      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_NEW);
    });

    it("runs delete by confirming and then deleting the selected row", () => {
      component.selector.selectRow(caConnectorServiceMock.caConnectors()[0]);

      toolbarAction("delete").run?.();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
      expect(caConnectorServiceMock.deleteCaConnector).not.toHaveBeenCalled();
      confirmClosed.next(true);
      confirmClosed.complete();

      expect(caConnectorServiceMock.deleteCaConnector).toHaveBeenCalledTimes(1);
      expect(caConnectorServiceMock.deleteCaConnector).toHaveBeenCalledWith("conn1");
    });

    it("runs create from its rendered button", () => {
      setRights(["caconnectorread"]);
      const navigate = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
      navigate.mockClear();

      toolbarButton("Create CA Connector")?.click();

      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS_NEW);
    });

    it("runs delete from its rendered button once a row is selected", () => {
      setRights(["caconnectorread"]);
      component.selector.selectRow(caConnectorServiceMock.caConnectors()[0]);
      fixture.detectChanges();

      toolbarButton("Delete")?.click();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
    });
  });
});
