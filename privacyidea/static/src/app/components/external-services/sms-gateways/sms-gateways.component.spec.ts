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
import { SaveAndExitDialogResult } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { expectsTableStateGating } from "@testing/table-state-gating";
import {
  MockAuthService,
  MockDialogService,
  MockSmsGatewayService,
  MockTableUtilsService
} from "@testing/mock-services";
import { Subject } from "rxjs";
import { SmsGatewaysComponent } from "./sms-gateways.component";

describe("SmsGatewaysComponent", () => {
  let component: SmsGatewaysComponent;
  let fixture: ComponentFixture<SmsGatewaysComponent>;
  let smsGatewayServiceMock: MockSmsGatewayService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<SaveAndExitDialogResult>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SmsGatewaysComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: SmsGatewayService, useClass: MockSmsGatewayService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    smsGatewayServiceMock = TestBed.inject(SmsGatewayService) as unknown as MockSmsGatewayService;
    smsGatewayServiceMock.smsGateways.set([
      { name: "gw1", providermodule: "mod1", options: {}, headers: {} },
      { name: "gw2", providermodule: "mod2", options: {}, headers: {} }
    ]);

    fixture = TestBed.createComponent(SmsGatewaysComponent);
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
      right: "smsgateway_read"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display gateways from service", () => {
    expect(component.smsDataSource().data.length).toBe(2);
    expect(component.smsDataSource().data[0].name).toBe("gw1");
  });

  it("should filter gateways", () => {
    component.onFilterInput("gw1");
    expect(component.smsDataSource().filter).toBe("gw1");
  });

  it("should navigate to create page", () => {
    component.onCreateNewGateway();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS_NEW);
  });

  it("should navigate to edit page when editing a gateway", () => {
    const gateway = smsGatewayServiceMock.smsGateways()[0];
    component.onEditGateway(gateway);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS_DETAILS + gateway.name);
  });

  it("should only select the gateways left by the filter", async () => {
    component.onFilterInput("gw1");
    fixture.detectChanges();
    await fixture.whenStable();

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((row) => row.name)).toEqual(["gw1"]);
  });

  it("should delete the selected gateways after confirmation", () => {
    const gateway = smsGatewayServiceMock.smsGateways()[0];
    component.selector.selectRow(gateway);
    component.deleteSelected();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next("discard");
    confirmClosed.complete();
    expect(smsGatewayServiceMock.deleteSmsGateway).toHaveBeenCalledWith("gw1");
    expect(component.selector.selectedCount()).toBe(0);
  });

  it("should not open the dialog when nothing is selected", () => {
    component.deleteSelected();
    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
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
      expect(toolbarAction("create").label).toBe("Create SMS Gateway");
      expect(toolbarAction("delete").label).toBe("Delete");
    });

    it("shows both actions while the read right is granted", () => {
      setRights(["smsgateway_read"]);

      expect(component["toolbarActions"]().every((action) => action.visible !== false)).toBe(true);
      expect(toolbarButton("Create SMS Gateway")).toBeTruthy();
      expect(toolbarButton("Delete")).toBeTruthy();
    });

    it("draws no toolbar while the read right is denied", () => {
      setRights([]);

      expect(fixture.nativeElement.querySelector("app-table-actions")).toBeNull();
      expect(toolbarButton("Create SMS Gateway")).toBeUndefined();
    });

    it("keeps create enabled and disables delete until a row is selected", () => {
      setRights(["smsgateway_read"]);

      expect(toolbarAction("create").disabled).toBeFalsy();
      expect(toolbarAction("delete").disabled).toBe(true);
      expect(toolbarButton("Create SMS Gateway")?.disabled).toBe(false);
      expect(toolbarButton("Delete")?.disabled).toBe(true);

      component.selector.selectRow(smsGatewayServiceMock.smsGateways()[0]);
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
      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS_NEW);
    });

    it("runs delete by confirming and then deleting the selected row", () => {
      component.selector.selectRow(smsGatewayServiceMock.smsGateways()[0]);

      toolbarAction("delete").run?.();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
      expect(smsGatewayServiceMock.deleteSmsGateway).not.toHaveBeenCalled();
      confirmClosed.next("discard");
      confirmClosed.complete();

      expect(smsGatewayServiceMock.deleteSmsGateway).toHaveBeenCalledTimes(1);
      expect(smsGatewayServiceMock.deleteSmsGateway).toHaveBeenCalledWith("gw1");
    });

    it("runs create from its rendered button", () => {
      setRights(["smsgateway_read"]);
      const navigate = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
      navigate.mockClear();

      toolbarButton("Create SMS Gateway")?.click();

      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS_NEW);
    });

    it("runs delete from its rendered button once a row is selected", () => {
      setRights(["smsgateway_read"]);
      component.selector.selectRow(smsGatewayServiceMock.smsGateways()[0]);
      fixture.detectChanges();

      toolbarButton("Delete")?.click();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
    });
  });
});
