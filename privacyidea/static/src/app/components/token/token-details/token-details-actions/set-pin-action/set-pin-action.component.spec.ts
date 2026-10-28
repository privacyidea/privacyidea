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
import { MatDialog, MatDialogRef } from "@angular/material/dialog";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import { MockLocalService, MockNotificationService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { hasError } from "@utils/form-state.utils";
import { of } from "rxjs";
import { SetPinActionComponent } from "./set-pin-action.component";

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
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn()
  };

  const pinInputs = (): HTMLInputElement[] => Array.from(fixture.nativeElement.querySelectorAll("input[matInput]"));
  const typeInto = (input: HTMLInputElement, value: string) => {
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };
  const setPinButton = (): HTMLButtonElement => fixture.nativeElement.querySelector(".set-pin-buttons button");

  beforeEach(async () => {
    jest.clearAllMocks();
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
    }).compileComponents();

    fixture = TestBed.createComponent(SetPinActionComponent);
    component = fixture.componentInstance;
    (TestBed.inject(AuthService) as unknown as MockAuthService).actionAllowed.mockReturnValue(true);
    component.setPinValue.set("1234");
    component.repeatPinValue.set("1234");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("setPin() success", () => {
    component.setPin();
    expect(tokenServiceStub.setPin).toHaveBeenCalledWith("Mock serial", "1234");
    expect(notificationServiceStub.success).toHaveBeenCalledWith("PIN set successfully.");
  });

  it("setPin() clears both PINs and the field state after success", () => {
    component.repeatPinForm().markAsTouched();
    component.setPin();
    expect(component.setPinValue()).toBe("");
    expect(component.repeatPinValue()).toBe("");
    expect(component.repeatPinForm().touched()).toBe(false);
  });

  it("setPin() should raise error if pins does not match", () => {
    component.repeatPinValue.set("4321");
    component.setPin();
    expect(tokenServiceStub.setPin).not.toHaveBeenCalled();
    expect(notificationServiceStub.warning).toHaveBeenCalledWith("PINs do not match.");
    expect(component.repeatPinForm().touched()).toBe(true);
  });

  it("typing into the PIN fields updates the models", () => {
    const [pin, repeat] = pinInputs();
    typeInto(pin, "9876");
    typeInto(repeat, "9876");
    expect(component.setPinValue()).toBe("9876");
    expect(component.repeatPinValue()).toBe("9876");
    expect(component.repeatPinForm().valid()).toBe(true);
    expect(setPinButton().disabled).toBe(false);
  });

  it("a differing repeat reports pinMismatch, shows the error and disables the button", () => {
    const [, repeat] = pinInputs();
    typeInto(repeat, "4321");
    repeat.dispatchEvent(new Event("blur"));
    fixture.detectChanges();
    expect(hasError(component.repeatPinForm, "pinMismatch")).toBe(true);
    expect(setPinButton().disabled).toBe(true);
    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("PINs do not match.");
  });

  it("changing the PIN re-evaluates the repeat", () => {
    expect(component.repeatPinForm().valid()).toBe(true);
    component.setPinValue.set("other");
    expect(component.repeatPinForm().valid()).toBe(false);
  });

  it("setRandomPin()", () => {
    component.setRandomPin();
    expect(matDialogStub.open).toHaveBeenCalled();
    expect(tokenServiceStub.setRandomPin).toHaveBeenCalled();
  });
});
