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
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import { ValidateCheckResponse, ValidateService } from "@services/validate/validate.service";
import { MockNotificationService, MockTokenService, MockValidateService } from "@testing/mock-services";
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

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TestOtpPinActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TestOtpPinActionComponent);
    component = fixture.componentInstance;
    validateService = TestBed.inject(ValidateService);
    notificationService = TestBed.inject(NotificationService);
    tokenService = TestBed.inject(TokenService);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
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
    jest
      .spyOn(validateService, "testToken")
      .mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));

    component.testToken();

    expect(notificationService.success).toHaveBeenCalled();
  });

  it("should notify a warning when the token is rejected", () => {
    jest
      .spyOn(validateService, "testToken")
      .mockReturnValue(of(mockValidateCheckResponse("REJECT")));

    component.testToken();

    expect(notificationService.warning).toHaveBeenCalled();
  });
});
