/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { SetPinActionComponent } from "./set-pin-action.component";
import { of } from "rxjs";
import { MatDialog, MatDialogRef } from "@angular/material/dialog";
import { TokenService } from "../../../../../services/token/token.service";
import { signal } from "@angular/core";
import { NotificationService } from "../../../../../services/notification/notification.service";
import { AuthService } from "../../../../../services/auth/auth.service";
import { MockAuthService, MockLocalService, MockNotificationService } from "../../../../../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("SetPinActionComponent", () => {
  let component: SetPinActionComponent;
  let fixture: ComponentFixture<SetPinActionComponent>;

  const tokenServiceStub = {
    setPin: jest.fn().mockReturnValue(of({ result: { status: true, value: 1 } })),
    setRandomPin: jest.fn().mockReturnValue(of({ detail: { pin: "1234" } })),
    tokenSerial: signal<string>("Mock serial")
  } as unknown as TokenService;

  const matDialogRefStub = {
    afterClosed: () => of(true)
  } as unknown as MatDialogRef<SetPinActionComponent>;

  const matDialogStub = {
    open: jest.fn().mockReturnValue(matDialogRefStub)
  } as unknown as MatDialog;

  const notificationServiceStub = {
    openSnackBar: jest.fn()
  };

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [SetPinActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: tokenServiceStub },
        { provide: MatDialog, useValue: matDialogStub },
        { provide: NotificationService, useValue: notificationServiceStub },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(SetPinActionComponent);
    component = fixture.componentInstance;
    component.setPinValue = signal("1234");
    component.repeatPinValue = signal("1234");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("setPin() success", () => {
    component.setPin();
    expect(tokenServiceStub.setPin).toHaveBeenCalledWith("Mock serial", "1234");
    expect(notificationServiceStub.openSnackBar).toHaveBeenCalledWith("PIN set successfully.");
  });

  it("setPin() should raise error if pins does not match", () => {
    component.repeatPinValue.set("4321");
    component.setPin();
    expect(tokenServiceStub.setPin).not.toHaveBeenCalled();
    expect(notificationServiceStub.openSnackBar).toHaveBeenCalledWith("PINs do not match.");
  });

  it("setRandomPin()", () => {
    component.setRandomPin();
    expect(matDialogStub.open).toHaveBeenCalled();
    expect(tokenServiceStub.setRandomPin).toHaveBeenCalled();
  });
});
