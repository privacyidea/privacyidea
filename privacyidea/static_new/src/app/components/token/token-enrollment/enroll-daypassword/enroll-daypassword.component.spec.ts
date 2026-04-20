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

import { EnrollDaypasswordComponent } from "./enroll-daypassword.component";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockSystemService } from "../../../../../testing/mock-services";
import { SystemService } from "../../../../services/system/system.service";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { AuthService } from "../../../../services/auth/auth.service";
import {
  DAYPASSWORD_HASHLIB, DAYPASSWORD_OTP_LENGTH,
  DAYPASSWORD_TIME_STEP,
  TOTP_HASHLIB,
  TOTP_TIME_STEP
} from "../../../../constants/token.constants";

describe("EnrollDaypasswordComponent", () => {
  let component: EnrollDaypasswordComponent;
  let fixture: ComponentFixture<EnrollDaypasswordComponent>;
  let systemService: MockSystemService;
  let authService: MockAuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollDaypasswordComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: AuthService, useClass: MockAuthService }]
    }).compileComponents();

    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;

    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("Check default values are set correctly on init", () => {
    expect(component.generateOnServerControl.value).toBe(true);
    expect(component.generateOnServerControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
    expect(component.otpLengthControl.value).toBe(6);
    expect(component.otpLengthControl.disabled).toBe(false);
    expect(component.hashAlgorithmControl.value).toBe("sha1");
    expect(component.hashAlgorithmControl.disabled).toBe(false);
    expect(component.timeStepControl.value).toBe("24h");
    expect(component.timeStepControl.disabled).toBe(false);
  });

  it("Default values are also set correctly if config contains empty strings", () => {
    const mockConfig = {
      [DAYPASSWORD_HASHLIB]: "",
      [DAYPASSWORD_TIME_STEP]: ""
    };
    systemService.systemConfig.set(mockConfig);
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.generateOnServerControl.value).toBe(true);
    expect(component.generateOnServerControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
    expect(component.otpLengthControl.value).toBe(6);
    expect(component.otpLengthControl.disabled).toBe(false);
    expect(component.hashAlgorithmControl.value).toBe("sha1");
    expect(component.hashAlgorithmControl.disabled).toBe(false);
    expect(component.timeStepControl.value).toBe("24h");
    expect(component.timeStepControl.disabled).toBe(false);
  });

  it("Default values from system config are used", () => {
    const mockConfig = {
      [TOTP_HASHLIB]: "sha256",
      [TOTP_TIME_STEP]: 60,
      [DAYPASSWORD_HASHLIB]: "sha512",
      [DAYPASSWORD_TIME_STEP]: "12h"
    };
    systemService.systemConfig.set(mockConfig);
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.hashAlgorithmControl.value).toBe("sha512");
    expect(component.hashAlgorithmControl.disabled).toBe(false);
    expect(component.timeStepControl.value).toBe("12h");
    expect(component.timeStepControl.disabled).toBe(false);
  });

  it("Uses policy values for hashlib, otplen, and time step over system config defaults", () => {
    const mockConfig = {
      [DAYPASSWORD_HASHLIB]: "sha512",
      [DAYPASSWORD_TIME_STEP]: "12h"
    };
    systemService.systemConfig.set(mockConfig);
    authService.rightsWithValues.set({
      [DAYPASSWORD_HASHLIB]: "sha256",
      [DAYPASSWORD_OTP_LENGTH]: "8",
      [DAYPASSWORD_TIME_STEP]: "48h"
    });
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    function checkPolicyEnforcedValues() {
      expect(component.hashAlgorithmControl.value).toBe("sha256");
      expect(component.hashAlgorithmControl.disabled).toBe(true);
      expect(component.timeStepControl.value).toBe("48h");
      expect(component.timeStepControl.disabled).toBe(true);
      expect(component.otpLengthControl.value).toBe(8);
      expect(component.otpLengthControl.disabled).toBe(true);
    }

    checkPolicyEnforcedValues();

    // disable - enable all controls should not change policy-enforced values
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    checkPolicyEnforcedValues();

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    checkPolicyEnforcedValues();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "daypassword",
        otpKey: "otp-key-123",
        otpLength: 8,
        hashAlgorithm: "SHA512",
        timeStep: "12h",
        generateOnServer: false
      });
      component.ngOnInit();
      expect(component.otpKeyFormControl.value).toBe("otp-key-123");
      expect(component.otpLengthControl.value).toBe(8);
      expect(component.hashAlgorithmControl.value).toBe("SHA512");
      expect(component.timeStepControl.value).toBe("12h");
      expect(component.generateOnServerControl.value).toBe(false);
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "daypassword",
        otpKey: undefined,
        otpLength: undefined,
        hashAlgorithm: undefined,
        timeStep: undefined,
        generateOnServer: undefined
      });
      component.ngOnInit();
      expect(component.otpKeyFormControl.value).toBe("");
      expect(component.otpLengthControl.value).toBe(6);
      expect(component.hashAlgorithmControl.value).toBe("sha256");
      expect(component.timeStepControl.value).toBe("24h");
      expect(component.generateOnServerControl.value).toBe(true);
    });
  });
});
