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

import { TestOtpPinActionComponent } from "./test-otp-pin-action.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ValidateService } from "../../../../../services/validate/validate.service";
import { TokenService } from "../../../../../services/token/token.service";
import { MockTokenService } from "../../../../../../testing/mock-services";

describe("TestOtpPinActionComponent", () => {
  let component: TestOtpPinActionComponent;
  let fixture: ComponentFixture<TestOtpPinActionComponent>;
  let validateService: ValidateService;
  let tokenService: TokenService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TestOtpPinActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(TestOtpPinActionComponent);
    component = fixture.componentInstance;
    validateService = TestBed.inject(ValidateService);
    tokenService = TestBed.inject(TokenService);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should test and verify token", () => {
    const testSpy = jest.spyOn(validateService, "testToken");
    component.otpOrPinToTest = "1234";
    tokenService.tokenSerial.set("Mock serial");

    component.testToken();
    component.verifyOTPValue();

    expect(testSpy).toHaveBeenCalledWith("Mock serial", "1234");
  });
});
