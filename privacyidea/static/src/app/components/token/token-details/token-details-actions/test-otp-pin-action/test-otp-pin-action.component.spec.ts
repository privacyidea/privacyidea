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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import { TriggerChallengeResponse, ValidateCheckResponse, ValidateService } from "@services/validate/validate.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockNotificationService, MockTokenService, MockValidateService } from "@testing/mock-services";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of } from "rxjs";
import { TestOtpPinActionComponent } from "./test-otp-pin-action.component";

function mockValidateCheckResponse(authentication: "ACCEPT" | "REJECT"): ValidateCheckResponse {
  return {
    id: 1,
    jsonrpc: "2.0",
    detail: {},
    result: { authentication, status: true },
    signature: "",
    time: Date.now(),
    version: "1.0",
    versionnumber: "1.0"
  };
}

describe("TestOtpPinActionComponent", () => {
  let component: TestOtpPinActionComponent;
  let fixture: ComponentFixture<TestOtpPinActionComponent>;
  let validateService: ValidateService;
  let notificationService: NotificationService;
  let tokenService: TokenService;
  let authService: MockAuthService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TestOtpPinActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TestOtpPinActionComponent);
    component = fixture.componentInstance;
    validateService = TestBed.inject(ValidateService);
    notificationService = TestBed.inject(NotificationService);
    tokenService = TestBed.inject(TokenService);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("typing into the field updates the model", () => {
    const input: HTMLInputElement = fixture.nativeElement.querySelector("input[matInput]");
    input.value = "654321";
    input.dispatchEvent(new Event("input"));
    expect(component.otpOrPinToTest()).toBe("654321");
  });

  it("the toggle button switches the input between masked and plain text", () => {
    const input: HTMLInputElement = fixture.nativeElement.querySelector("input[matInput]");
    const toggle: HTMLButtonElement = fixture.nativeElement.querySelector("button[matSuffix]");
    expect(input.type).toBe("password");
    toggle.click();
    fixture.detectChanges();
    expect(component.hide()).toBe(false);
    expect(input.type).toBe("text");
    toggle.click();
    fixture.detectChanges();
    expect(input.type).toBe("password");
  });

  it("should test and verify token", () => {
    const testSpy = jest.spyOn(validateService, "testToken");
    component.otpOrPinToTest.set("1234");
    tokenService.tokenSerial.set("Mock serial");

    component.testToken();
    component.verifyOTPValue();

    expect(testSpy).toHaveBeenCalledWith("Mock serial", "1234");
  });

  it("should notify success when the token is accepted", () => {
    jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));

    component.testToken();

    expect(notificationService.success).toHaveBeenCalled();
  });

  it("should notify a warning when the token is rejected", () => {
    jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("REJECT")));

    component.testToken();

    expect(notificationService.warning).toHaveBeenCalled();
  });

  describe("Test without PIN", () => {
    const testWithoutPinButton = (): HTMLButtonElement | undefined =>
      Array.from(fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>).find((button) =>
        button.textContent?.includes("Test without PIN")
      );

    it("hides the button without the triggerchallenge right", () => {
      authService.actionAllowed.mockReturnValue(false);
      fixture.detectChanges();
      expect(testWithoutPinButton()).toBeUndefined();
    });

    it("shows the button with the triggerchallenge right", () => {
      authService.actionAllowed.mockImplementation((action: string) => action === "triggerchallenge");
      fixture.detectChanges();
      expect(testWithoutPinButton()).toBeDefined();
    });

    it("triggers a challenge for the token when the button is clicked", () => {
      authService.actionAllowed.mockImplementation((action: string) => action === "triggerchallenge");
      fixture.detectChanges();
      tokenService.tokenSerial.set("HOTP0001");

      testWithoutPinButton()?.click();

      expect(validateService.triggerChallenge).toHaveBeenCalledWith("HOTP0001");
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });

    it("notifies success with the message of the challenge", () => {
      component.testWithoutPin();

      expect(notificationService.success).toHaveBeenCalledWith("Challenge triggered. please enter otp: ");
    });

    it("notifies a warning if the server created no challenge", () => {
      jest
        .spyOn(validateService, "triggerChallenge")
        .mockReturnValue(of(MockPiResponse.fromValue<number, TriggerChallengeResponse["detail"]>(0, {})));

      component.testWithoutPin();

      expect(notificationService.warning).toHaveBeenCalledWith(
        "No challenge triggered. The token must be active and support challenge-response."
      );
      expect(notificationService.success).not.toHaveBeenCalled();
    });
  });
});
