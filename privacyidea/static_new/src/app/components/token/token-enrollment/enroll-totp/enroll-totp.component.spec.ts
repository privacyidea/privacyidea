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

import { EnrollTotpComponent } from "./enroll-totp.component";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../../../../services/auth/auth.service";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { MockSystemService } from "../../../../../testing/mock-services";
import { SystemService } from "../../../../services/system/system.service";
import { HOTP_HASHLIB, TOTP_HASHLIB, TOTP_OTP_LENGTH, TOTP_TIME_STEP } from "../../../../constants/token.constants";

describe("EnrollTotpComponent", () => {
  let component: EnrollTotpComponent;
  let fixture: ComponentFixture<EnrollTotpComponent>;
  let authService: MockAuthService;
  let systemService: MockSystemService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTotpComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: SystemService, useClass: MockSystemService }]
    }).compileComponents();

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;

    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("Check default values are set correctly on init", () => {
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
    expect(component.otpLengthFormControl.value).toBe(6);
    expect(component.otpLengthFormControl.disabled).toBe(false);
    expect(component.hashAlgorithmControl.value).toBe("sha1");
    expect(component.hashAlgorithmControl.disabled).toBe(false);
    expect(component.timeStepControl.value).toBe(30);
    expect(component.timeStepControl.disabled).toBe(false);
  });

  it("Default values are also set correctly if config contains empty strings", () => {
    const mockConfig = {
      [TOTP_HASHLIB]: "",
      [TOTP_TIME_STEP]: ""
    };
    systemService.systemConfig.set(mockConfig);
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
    expect(component.otpLengthFormControl.value).toBe(6);
    expect(component.otpLengthFormControl.disabled).toBe(false);
    expect(component.hashAlgorithmControl.value).toBe("sha1");
    expect(component.hashAlgorithmControl.disabled).toBe(false);
    expect(component.timeStepControl.value).toBe(30);
    expect(component.timeStepControl.disabled).toBe(false);
  });

  it("Default values from system config are used", () => {
    const mockConfig = {
      [TOTP_HASHLIB]: "sha256",
      [TOTP_TIME_STEP]: "60",
      [HOTP_HASHLIB]: "sha512"
    };
    systemService.systemConfig.set(mockConfig);
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.hashAlgorithmControl.value).toBe("sha256");
    expect(component.hashAlgorithmControl.disabled).toBe(false);
    expect(component.timeStepControl.value).toBe(60);
    expect(component.timeStepControl.disabled).toBe(false);
  });

  it("Uses policy values for hashlib, otplen, and time step over system config defaults", () => {
    const mockConfig = {
      [TOTP_HASHLIB]: "sha256",
      [TOTP_TIME_STEP]: 60
    };
    systemService.systemConfig.set(mockConfig);
    authService.rightsWithValues.set({ [TOTP_HASHLIB]: "sha512", [TOTP_OTP_LENGTH]: "8", [TOTP_TIME_STEP]: "45" });
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    function checkPolicyEnforcedValues() {
      expect(component.hashAlgorithmControl.value).toBe("sha512");
      expect(component.hashAlgorithmControl.disabled).toBe(true);
      expect(component.timeStepControl.value).toBe(45);
      expect(component.timeStepControl.disabled).toBe(true);
      expect(component.otpLengthFormControl.value).toBe(8);
      expect(component.otpLengthFormControl.disabled).toBe(true);
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

  it("should disable/enable all controls according to disable input", () => {
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();

    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);
    expect(component.otpLengthFormControl.disabled).toBe(true);
    expect(component.hashAlgorithmControl.disabled).toBe(true);
    expect(component.timeStepControl.disabled).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();

    expect(component.generateOnServerFormControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.disabled).toBe(true);
    component.otpKeyFormControl.markAsTouched();
    expect(component.otpKeyFormControl.invalid).toBe(false);
    expect(component.otpLengthFormControl.disabled).toBe(false);
    expect(component.hashAlgorithmControl.disabled).toBe(false);
    expect(component.timeStepControl.disabled).toBe(false);
  });

  it("disables generateOnServer when policy forces server-side key generation", () => {
    authService.checkForceServerGenerateOTPKey.mockReturnValue(true);
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    component.ngOnInit();

    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);

    component.generateOnServerFormControl.setValue(false);
    expect(component.otpKeyFormControl.disabled).toBe(true);
    component.generateOnServerFormControl.setValue(true);

    // Should stay disabled regardless of the disabled input
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("toggles otpKey enablement & validators when generateOnServer changes", () => {
    authService.checkForceServerGenerateOTPKey.mockReturnValue(false);
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    component.ngOnInit();

    expect(component.otpKeyFormControl.disabled).toBe(true);

    component.generateOnServerFormControl.setValue(false);
    expect(component.otpKeyFormControl.enabled).toBe(true);

    component.otpKeyFormControl.setValue("");
    component.otpKeyFormControl.markAsTouched();
    expect(component.otpKeyFormControl.invalid).toBe(true);

    // disable - enable all controls should restore same state
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    expect(component.generateOnServerFormControl.value).toBe(false);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    expect(component.generateOnServerFormControl.value).toBe(false);
    expect(component.generateOnServerFormControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.disabled).toBe(false);

    // Set back to generate on server should disable otp key again
    component.generateOnServerFormControl.setValue(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("disables 2step control if policy totp_2step is set to force", () => {
    authService.check2Step.mockReturnValue("force");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    component.ngOnInit();

    // 2-step checkbox should be present
    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector("mat-checkbox[formcontrolname=\"twoStepControl\"]");
    expect(twoStepCheckbox).toBeDefined();

    expect(component.twoStepControl.value).toBe(true);
    expect(component.twoStepControl.disabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);

    // should stay disabled regardless of the disabled input
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    expect(component.twoStepControl.value).toBe(true);
    expect(component.twoStepControl.disabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    expect(component.twoStepControl.value).toBe(true);
    expect(component.twoStepControl.disabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("enable 2step control if policy totp_2step is set to allow", () => {
    authService.check2Step.mockReturnValue("allow");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    component.ngOnInit();

    // 2-step checkbox should be present
    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector("mat-checkbox[formcontrolname=\"twoStepControl\"]");
    expect(twoStepCheckbox).toBeDefined();

    expect(component.twoStepControl.value).toBe(false);
    expect(component.twoStepControl.enabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.enabled).toBe(true);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("selecting 2 step should select and disable generate on server input", () => {
    authService.check2Step.mockReturnValue("allow");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    component.ngOnInit();

    // Set OTP Key
    component.generateOnServerFormControl.setValue(false);
    component.otpKeyFormControl.setValue("ABC123");

    expect(component.twoStepControl.value).toBe(false);
    expect(component.twoStepControl.enabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(false);
    expect(component.generateOnServerFormControl.enabled).toBe(true);
    expect(component.otpKeyFormControl.value).toEqual("ABC123");
    expect(component.otpKeyFormControl.disabled).toBe(false);

    // Select 2-step should clear otp key and select generate on server
    component.twoStepControl.setValue(true);

    expect(component.twoStepControl.value).toBe(true);
    expect(component.twoStepControl.enabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.enabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);

    // disable - enable all controls should restore same state
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();
    expect(component.twoStepControl.value).toBe(true);
    expect(component.twoStepControl.disabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);

    fixture.componentRef.setInput("disabled", false);
    fixture.detectChanges();
    expect(component.twoStepControl.value).toBe(true);
    expect(component.twoStepControl.disabled).toBe(false);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("hide 2step input if policy totp_2step is disabled", () => {
    authService.check2Step.mockReturnValue("disabled");
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    component.ngOnInit();

    // 2-step checkbox should NOT be present
    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector("mat-checkbox[formcontrolname=\"twoStepControl\"]");
    expect(twoStepCheckbox).toBeNull();

    expect(component.twoStepControl.value).toBe(false);
    expect(component.twoStepControl.enabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.enabled).toBe(true);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
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
      component.ngOnInit();
      expect(component.generateOnServerFormControl.value).toBe(false);
      expect(component.otpLengthFormControl.value).toBe(8);
      expect(component.hashAlgorithmControl.value).toBe("sha512");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "totp",
        generateOnServer: undefined,
        otpLength: undefined,
        hashAlgorithm: undefined,
        timeStep: undefined
      });
      component.ngOnInit();
      expect(component.generateOnServerFormControl.value).toBe(true);
      expect(component.otpLengthFormControl.value).toBe(6);
      expect(component.hashAlgorithmControl.value).toBe("sha1");
    });
  });
});
