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
import { NewSmsGatewayComponent } from "./new-sms-gateway.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";
import { SmsGatewayService } from "../../../../services/sms-gateway/sms-gateway.service";
import { signal } from "@angular/core";

describe("NewSmsGatewayComponent", () => {
  let component: NewSmsGatewayComponent;
  let fixture: ComponentFixture<NewSmsGatewayComponent>;
  let smsGatewayServiceMock: any;
  let dialogRefMock: any;
  let dialogMock: any;

  beforeEach(async () => {
    smsGatewayServiceMock = {
      smsProvidersResource: { value: signal({
        result: { value: {
          mod1: { parameters: { p1: { description: "desc1" } } }
        } }
      }) },
      postSmsGateway: jest.fn().mockResolvedValue(true),
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
      imports: [NewSmsGatewayComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: SmsGatewayService, useValue: smsGatewayServiceMock },
      ]
    }).overrideComponent(NewSmsGatewayComponent, {
      add: {
        providers: [
          { provide: MatDialog, useValue: dialogMock }
        ]
      }
    }).compileComponents();

    fixture = TestBed.createComponent(NewSmsGatewayComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode).toBe(false);
    expect(component.smsForm.get("name")?.value).toBe("");
  });

  it("should update form when provider changes", async () => {
    component.smsForm.get("providermodule")?.setValue("mod1");
    fixture.detectChanges();
    await fixture.whenStable();
    expect(component.parametersForm.get("p1")).toBeDefined();
  });

  it("should call save when form is valid", async () => {
    component.smsForm.patchValue({
      name: "test",
      providermodule: "mod1"
    });
    component.smsForm.get("options")?.patchValue({ p1: "val1" });
    await component.save();
    expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalled();
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });
});
