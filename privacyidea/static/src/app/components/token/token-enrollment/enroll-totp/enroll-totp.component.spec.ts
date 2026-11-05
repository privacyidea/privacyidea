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
import { TOTP_HASHLIB, TOTP_OTP_LENGTH, TOTP_TIME_STEP } from "@constants/token.constants";
import { AuthService } from "@services/auth/auth.service";
import { SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import { MockSystemService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { EnrollTotpComponent } from "./enroll-totp.component";
import {
  clearOverlays,
  clickCheckbox,
  flushFixture,
  matSelectAt,
  pickOption,
  typeInto
} from "@testing/enroll-form-dom";

describe("EnrollTotpComponent", () => {
  let component: EnrollTotpComponent;
  let fixture: ComponentFixture<EnrollTotpComponent>;
  let authService: MockAuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTotpComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: SystemService, useClass: MockSystemService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;

    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("Check default values are set correctly on init", () => {
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
    expect(component.otpLength()).toBe(6);
    expect(component.otpLengthForm().disabled()).toBe(false);
    expect(component.hashAlgorithm()).toBe("sha1");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.timeStep()).toBe(30);
    expect(component.timeStepForm().disabled()).toBe(false);
  });

  it("Uses policy values for hashlib, otplen, and time step", () => {
    authService.rightsWithValues.set({ [TOTP_HASHLIB]: "sha512", [TOTP_OTP_LENGTH]: "8", [TOTP_TIME_STEP]: "45" });
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    function checkPolicyEnforcedValues() {
      expect(component.hashAlgorithm()).toBe("sha512");
      expect(component.hashAlgorithmForm().disabled()).toBe(true);
      expect(component.timeStep()).toBe(45);
      expect(component.timeStepForm().disabled()).toBe(true);
      expect(component.otpLength()).toBe(8);
      expect(component.otpLengthForm().disabled()).toBe(true);
    }

    checkPolicyEnforcedValues();

    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    checkPolicyEnforcedValues();

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    checkPolicyEnforcedValues();
  });

  it("should disable/enable all controls according to disable input", () => {
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();

    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
    expect(component.otpLengthForm().disabled()).toBe(true);
    expect(component.hashAlgorithmForm().disabled()).toBe(true);
    expect(component.timeStepForm().disabled()).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();

    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKeyForm().disabled()).toBe(true);
    expect(component.otpLengthForm().disabled()).toBe(false);
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.timeStepForm().disabled()).toBe(false);
  });

  it("disables generateOnServer when policy forces server-side key generation", () => {
    authService.checkForceServerGenerateOTPKey.mockReturnValue(true);
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);

    // Should stay disabled regardless of the disabled input
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("toggles otpKey enablement & validators when generateOnServer changes", () => {
    authService.checkForceServerGenerateOTPKey.mockReturnValue(false);
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.otpKeyForm().disabled()).toBe(true);

    component.generateOnServer.set(false);
    fixture.detectChanges();
    expect(component.otpKeyForm().disabled()).toBe(false);

    component.otpKey.set("");
    component.otpKeyForm().markAsTouched();
    fixture.detectChanges();
    expect(component.otpKeyForm().valid()).toBe(false);

    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    expect(component.generateOnServer()).toBe(false);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    expect(component.generateOnServer()).toBe(false);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKeyForm().disabled()).toBe(false);

    // Set back to generate on server should disable otp key again
    component.generateOnServer.set(true);
    fixture.detectChanges();
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("disables 2step control if policy totp_2step is set to force", () => {
    authService.check2Step.mockReturnValue("force");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(true);
    expect(component.twoStepDisabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);

    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    expect(component.twoStepEnabled()).toBe(true);
    expect(component.twoStepDisabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("enable 2step control if policy totp_2step is set to allow", () => {
    authService.check2Step.mockReturnValue("allow");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(false);
    expect(component.twoStepDisabled()).toBe(false);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("selecting 2 step should select and disable generate on server input", () => {
    authService.check2Step.mockReturnValue("allow");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    component.generateOnServer.set(false);
    component.otpKey.set("ABC123");
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(false);
    expect(component.twoStepDisabled()).toBe(false);
    expect(component.generateOnServer()).toBe(false);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("ABC123");
    expect(component.otpKeyForm().disabled()).toBe(false);

    component.twoStepEnabled.set(true);
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("hide 2step input if policy totp_2step is disabled", () => {
    authService.check2Step.mockReturnValue("disabled");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector(
      'mat-checkbox[formcontrolname="twoStepControl"]'
    );
    expect(twoStepCheckbox).toBeNull();

    expect(component.twoStepEnabled()).toBe(false);
    expect(component.twoStepDisabled()).toBe(false);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "totp",
        generateOnServer: false,
        otpLength: 8,
        hashAlgorithm: "sha512",
        timeStep: 45
      });
      fixture.detectChanges();
      expect(component.generateOnServer()).toBe(false);
      expect(component.otpLength()).toBe(8);
      expect(component.hashAlgorithm()).toBe("sha512");
      expect(component.timeStep()).toBe(45);
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "totp",
        generateOnServer: undefined,
        otpLength: undefined,
        hashAlgorithm: undefined,
        timeStep: undefined
      });
      fixture.detectChanges();
      expect(component.generateOnServer()).toBe(true);
      expect(component.otpLength()).toBe(6);
      expect(component.hashAlgorithm()).toBe("sha1");
    });
  });

  describe("bound controls", () => {
    afterEach(clearOverlays);

    function recreate() {
      fixture = TestBed.createComponent(EnrollTotpComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
    }

    it("writes a click on the generate checkbox to the model and marks the field dirty", async () => {
      expect(component.generateOnServerForm().dirty()).toBe(false);

      await clickCheckbox(fixture, "mat-checkbox:not(.server-checkbox)");

      expect(component.generateOnServer()).toBe(false);
      expect(component.generateOnServerForm().dirty()).toBe(true);
    });

    it("writes a click on the two-step checkbox to the model", async () => {
      authService.check2Step.mockReturnValue("allow");
      recreate();

      await clickCheckbox(fixture, "mat-checkbox:first-of-type");

      expect(component.twoStepEnabled()).toBe(true);
      expect(component.twoStepEnabledForm().dirty()).toBe(true);
    });

    it("renders the checkboxes disabled while the policy forces the setting", () => {
      authService.check2Step.mockReturnValue("force");
      authService.checkForceServerGenerateOTPKey.mockReturnValue(true);
      recreate();

      expect(fixture.nativeElement.querySelectorAll("mat-checkbox input[type=checkbox]:disabled").length).toBe(2);
    });

    it("writes the picked OTP length, hash algorithm and timestep to the model", async () => {
      await pickOption(fixture, matSelectAt(fixture, 0), 1);
      await pickOption(fixture, matSelectAt(fixture, 1), 2);
      await pickOption(fixture, matSelectAt(fixture, 2), 1);

      expect(component.otpLength()).toBe(8);
      expect(component.hashAlgorithm()).toBe("sha512");
      expect(component.timeStep()).toBe(60);
      expect(component.timeStepForm().dirty()).toBe(true);
    });

    it("renders the OTP key errors once the field was touched", async () => {
      component.generateOnServer.set(false);
      await flushFixture(fixture);

      fixture.nativeElement.querySelector("input[matInput]").dispatchEvent(new Event("blur"));
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("OTP key is required");
      expect(fixture.nativeElement.textContent).toContain("OTP key must be at least 16 characters");
    });

    it("accepts a typed OTP key of at least 16 characters", async () => {
      component.generateOnServer.set(false);
      await flushFixture(fixture);

      await typeInto(fixture, fixture.nativeElement.querySelector("input[matInput]"), "0123456789abcdef");

      expect(component.otpKeyForm().valid()).toBe(true);
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();
    });
  });
});
