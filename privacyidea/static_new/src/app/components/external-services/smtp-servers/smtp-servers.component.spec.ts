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
import { Router, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SmtpServersComponent } from "@components/external-services/smtp-servers/smtp-servers.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockAuthService, MockDialogService, MockTableUtilsService } from "@testing/mock-services";
import { Subject } from "rxjs";

describe("SmtpServersComponent", () => {
  let component: SmtpServersComponent;
  let fixture: ComponentFixture<SmtpServersComponent>;
  let smtpServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;
  let router: Router;

  beforeEach(async () => {
    smtpServiceMock = {
      smtpServers: signal([
        { identifier: "server1", server: "smtp1.com", sender: "s1@test.com", tls: true, enqueue_job: false },
        { identifier: "server2", server: "smtp2.com", sender: "s2@test.com", tls: false, enqueue_job: true }
      ]),
      deleteSmtpServer: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [SmtpServersComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: SmtpService, useValue: smtpServiceMock },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

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

  it("should create", () => {
    expect(component).toBeTruthy();
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
    component.deleteServer(server);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();

    expect(smtpServiceMock.deleteSmtpServer).toHaveBeenCalledWith("server1");
  });
});
