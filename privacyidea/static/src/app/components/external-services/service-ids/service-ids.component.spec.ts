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
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ServiceIdsComponent } from "@components/external-services/service-ids/service-ids.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { ServiceIdService } from "@services/service-id/service-id.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { expectsTableStateGating } from "@testing/table-state-gating";
import {
  MockAuthService,
  MockDialogService,
  MockServiceIdService,
  MockTableUtilsService
} from "@testing/mock-services";
import { Subject } from "rxjs";

describe("ServiceIdsComponent", () => {
  let component: ServiceIdsComponent;
  let fixture: ComponentFixture<ServiceIdsComponent>;
  let serviceIdServiceMock: MockServiceIdService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ServiceIdsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ServiceIdService, useClass: MockServiceIdService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    serviceIdServiceMock = TestBed.inject(ServiceIdService) as unknown as MockServiceIdService;
    serviceIdServiceMock.serviceIds.set([
      { servicename: "service1", description: "desc1", id: 1 },
      { servicename: "service2", description: "desc2", id: 2 }
    ]);

    fixture = TestBed.createComponent(ServiceIdsComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
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
      right: "serviceid_list"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should only select the service IDs left by the filter", async () => {
    component.onFilterInput("service1");
    fixture.detectChanges();
    await fixture.whenStable();

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((row) => row.servicename)).toEqual(["service1"]);
  });

  it("should display service IDs from service", () => {
    expect(component.serviceIdDataSource().data.length).toBe(2);
    expect(component.serviceIdDataSource().data[0].servicename).toBe("service1");
  });

  it("should filter service IDs", () => {
    component.onFilterInput("service1");
    expect(component.serviceIdDataSource().filter).toBe("service1");
  });

  it("should navigate to edit page when editing a service ID", () => {
    const serviceId = serviceIdServiceMock.serviceIds()[0];
    component.onEditServiceId(serviceId);
    expect(router.navigateByUrl).toHaveBeenCalledWith(
      ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS_DETAILS + serviceId.servicename
    );
  });

  it("should navigate to create page", () => {
    component.onCreateNewServiceId();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS_NEW);
  });

  it("should delete service ID after confirmation", async () => {
    const serviceId = serviceIdServiceMock.serviceIds()[0];
    component.selector.selectRow(serviceId);
    component.deleteSelected();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();
    expect(serviceIdServiceMock.deleteServiceId).toHaveBeenCalledWith("service1");
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
      expect(toolbarAction("create").label).toBe("Create Service ID");
      expect(toolbarAction("delete").label).toBe("Delete");
    });

    it("shows both actions while the read right is granted", () => {
      setRights(["serviceid_list"]);

      expect(component["toolbarActions"]().every((action) => action.visible !== false)).toBe(true);
      expect(toolbarButton("Create Service ID")).toBeTruthy();
      expect(toolbarButton("Delete")).toBeTruthy();
    });

    it("draws no toolbar while the read right is denied", () => {
      setRights([]);

      expect(fixture.nativeElement.querySelector("app-table-actions")).toBeNull();
      expect(toolbarButton("Create Service ID")).toBeUndefined();
    });

    it("keeps create enabled and disables delete until a row is selected", () => {
      setRights(["serviceid_list"]);

      expect(toolbarAction("create").disabled).toBeFalsy();
      expect(toolbarAction("delete").disabled).toBe(true);
      expect(toolbarButton("Create Service ID")?.disabled).toBe(false);
      expect(toolbarButton("Delete")?.disabled).toBe(true);

      component.selector.selectRow(serviceIdServiceMock.serviceIds()[0]);
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
      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS_NEW);
    });

    it("runs delete by confirming and then deleting the selected row", () => {
      component.selector.selectRow(serviceIdServiceMock.serviceIds()[0]);

      toolbarAction("delete").run?.();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
      expect(serviceIdServiceMock.deleteServiceId).not.toHaveBeenCalled();
      confirmClosed.next(true);
      confirmClosed.complete();

      expect(serviceIdServiceMock.deleteServiceId).toHaveBeenCalledTimes(1);
      expect(serviceIdServiceMock.deleteServiceId).toHaveBeenCalledWith("service1");
    });

    it("runs create from its rendered button", () => {
      setRights(["serviceid_list"]);
      const navigate = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
      navigate.mockClear();

      toolbarButton("Create Service ID")?.click();

      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS_NEW);
    });

    it("runs delete from its rendered button once a row is selected", () => {
      setRights(["serviceid_list"]);
      component.selector.selectRow(serviceIdServiceMock.serviceIds()[0]);
      fixture.detectChanges();

      toolbarButton("Delete")?.click();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
    });
  });
});
