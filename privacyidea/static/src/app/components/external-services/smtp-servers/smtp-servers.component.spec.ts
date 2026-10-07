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
import { SmtpServersComponent } from "@components/external-services/smtp-servers/smtp-servers.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { MockAuthService, MockDialogService, MockSmtpService, MockTableUtilsService } from "@testing/mock-services";
import { Subject } from "rxjs";

describe("SmtpServersComponent", () => {
  let component: SmtpServersComponent;
  let fixture: ComponentFixture<SmtpServersComponent>;
  let smtpServiceMock: MockSmtpService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SmtpServersComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: SmtpService, useClass: MockSmtpService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    smtpServiceMock = TestBed.inject(SmtpService) as unknown as MockSmtpService;
    smtpServiceMock.smtpServers.set([
      {
        identifier: "server1",
        server: "smtp1.com",
        sender: "s1@test.com",
        tls: true,
        enqueue_job: false,
        port: 25,
        timeout: 10,
        smime: false,
        dont_send_on_error: false
      },
      {
        identifier: "server2",
        server: "smtp2.com",
        sender: "s2@test.com",
        tls: false,
        enqueue_job: true,
        port: 25,
        timeout: 10,
        smime: false,
        dont_send_on_error: false
      }
    ]);

    fixture = TestBed.createComponent(SmtpServersComponent);
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
      right: "smtpserver_read"
    });
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should only select the rows left by the filter", async () => {
    component.onFilterInput("server1");
    fixture.detectChanges();
    await fixture.whenStable();

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((row) => row.identifier)).toEqual(["server1"]);
  });

  it("should keep tracking the rendered rows after the data source is rebuilt", async () => {
    fixture.detectChanges();
    await fixture.whenStable();

    smtpServiceMock.smtpServers.set([
      { ...smtpServiceMock.smtpServers()[0], identifier: "server3" },
      { ...smtpServiceMock.smtpServers()[1], identifier: "server4" }
    ]);
    fixture.detectChanges();
    await fixture.whenStable();

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((row) => row.identifier)).toEqual(["server3", "server4"]);
  });

  it("should display servers from service", () => {
    expect(component.smtpDataSource().data.length).toBe(2);
    expect(component.smtpDataSource().data[0].identifier).toBe("server1");
  });

  it("should filter servers", () => {
    component.onFilterInput("server1");
    expect(component.smtpDataSource().filter).toBe("server1");
  });

  it("should navigate to create page", () => {
    component.onCreateNewServer();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP_NEW);
  });

  it("should navigate to edit page when editing a server", () => {
    const server = smtpServiceMock.smtpServers()[0];
    component.onEditServer(server);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP_DETAILS + server.identifier);
  });

  it("should delete server after confirmation", async () => {
    const server = smtpServiceMock.smtpServers()[0];
    component.selector.selectRow(server);
    component.deleteSelected();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();

    expect(smtpServiceMock.deleteSmtpServer).toHaveBeenCalledWith("server1");
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
      expect(toolbarAction("create").label).toBe("Create SMTP Server");
      expect(toolbarAction("delete").label).toBe("Delete");
    });

    it("shows both actions while the read right is granted", () => {
      setRights(["smtpserver_read"]);

      expect(component["toolbarActions"]().every((action) => action.visible !== false)).toBe(true);
      expect(toolbarButton("Create SMTP Server")).toBeTruthy();
      expect(toolbarButton("Delete")).toBeTruthy();
    });

    it("draws no toolbar while the read right is denied", () => {
      setRights([]);

      expect(fixture.nativeElement.querySelector("app-table-actions")).toBeNull();
      expect(toolbarButton("Create SMTP Server")).toBeUndefined();
    });

    it("keeps create enabled and disables delete until a row is selected", () => {
      setRights(["smtpserver_read"]);

      expect(toolbarAction("create").disabled).toBeFalsy();
      expect(toolbarAction("delete").disabled).toBe(true);
      expect(toolbarButton("Create SMTP Server")?.disabled).toBe(false);
      expect(toolbarButton("Delete")?.disabled).toBe(true);

      component.selector.selectRow(smtpServiceMock.smtpServers()[0]);
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
      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP_NEW);
    });

    it("runs delete by confirming and then deleting the selected row", () => {
      component.selector.selectRow(smtpServiceMock.smtpServers()[0]);

      toolbarAction("delete").run?.();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
      expect(smtpServiceMock.deleteSmtpServer).not.toHaveBeenCalled();
      confirmClosed.next(true);
      confirmClosed.complete();

      expect(smtpServiceMock.deleteSmtpServer).toHaveBeenCalledTimes(1);
      expect(smtpServiceMock.deleteSmtpServer).toHaveBeenCalledWith("server1");
    });

    it("runs create from its rendered button", () => {
      setRights(["smtpserver_read"]);
      const navigate = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
      navigate.mockClear();

      toolbarButton("Create SMTP Server")?.click();

      expect(navigate).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMTP_NEW);
    });

    it("runs delete from its rendered button once a row is selected", () => {
      setRights(["smtpserver_read"]);
      component.selector.selectRow(smtpServiceMock.smtpServers()[0]);
      fixture.detectChanges();

      toolbarButton("Delete")?.click();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SimpleConfirmationDialogComponent })
      );
    });
  });
});
