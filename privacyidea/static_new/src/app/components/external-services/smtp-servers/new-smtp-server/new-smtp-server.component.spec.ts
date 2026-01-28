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
import { NewSmtpServerComponent } from "./new-smtp-server.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { SmtpService } from "../../../../services/smtp/smtp.service";

describe("NewSmtpServerComponent", () => {
  let component: NewSmtpServerComponent;
  let fixture: ComponentFixture<NewSmtpServerComponent>;
  let smtpServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;

  beforeEach(async () => {
    smtpServiceMock = {
      postSmtpServer: jest.fn().mockResolvedValue(true),
      testSmtpServer: jest.fn().mockResolvedValue(true),
    };

    dialogRefMock = {
      disableClose: false,
      backdropClick: jest.fn().mockReturnValue(of()),
      keydownEvents: jest.fn().mockReturnValue(of()),
      close: jest.fn()
    };

    dialogMock = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) }),
    };

    await TestBed.configureTestingModule({
      imports: [NewSmtpServerComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: SmtpService, useValue: smtpServiceMock },
      ]
    }).overrideComponent(NewSmtpServerComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: dialogMock }
        ]
      }
    }).compileComponents();

    fixture = TestBed.createComponent(NewSmtpServerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode).toBe(false);
    expect(component.smtpForm.get("identifier")?.value).toBe("");
  });

  it("should call save when form is valid", async () => {
    component.smtpForm.patchValue({
      identifier: "test",
      server: "smtp.test.com",
      port: 25,
      sender: "test@test.com",
      timeout: 5
    });
    await component.save();
    expect(smtpServiceMock.postSmtpServer).toHaveBeenCalled();
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });

  it("should call test when form is valid", async () => {
    component.smtpForm.patchValue({
      identifier: "test",
      server: "smtp.test.com",
      port: 25,
      sender: "test@test.com",
      timeout: 5
    });
    await component.test();
    expect(smtpServiceMock.testSmtpServer).toHaveBeenCalled();
  });
});
