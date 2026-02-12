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
import { SmtpServersComponent } from "./smtp-servers.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { SmtpService } from "../../../services/smtp/smtp.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { signal } from "@angular/core";
import { Subject } from "rxjs";
import { MockMatDialogRef } from "src/testing/mock-mat-dialog-ref";
import { MockDialogService } from "src/testing/mock-services";

describe("SmtpServersComponent", () => {
  let component: SmtpServersComponent;
  let fixture: ComponentFixture<SmtpServersComponent>;
  let smtpServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  beforeEach(async () => {
    smtpServiceMock = {
      smtpServers: signal([
        { identifier: "server1", server: "smtp1.com", sender: "s1@test.com", tls: true, enqueue_job: false },
        { identifier: "server2", server: "smtp2.com", sender: "s2@test.com", tls: false, enqueue_job: true }
      ]),
      deleteSmtpServer: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [SmtpServersComponent, NoopAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SmtpService, useValue: smtpServiceMock },
        { provide: DialogService, useClass: MockDialogService }
      ]
    })
      .overrideComponent(SmtpServersComponent, {
        add: {
          providers: [{ provide: MatDialog, useValue: { open: jest.fn() } }]
        }
      })
      .compileComponents();

    fixture = TestBed.createComponent(SmtpServersComponent);

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

  it("should display servers from service", () => {
    expect(component.smtpDataSource().data.length).toBe(2);
    expect(component.smtpDataSource().data[0].identifier).toBe("server1");
  });

  it("should filter servers", () => {
    component.onFilterInput("server1");
    expect(component.smtpDataSource().filter).toBe("server1");
  });

  it("should open edit dialog", () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const server = smtpServiceMock.smtpServers()[0];
    component.openEditDialog(server);
    expect(dialog.open).toHaveBeenCalled();
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
