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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

import { TokenService } from "../../../../services/token/token.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { HotpApiPayloadMapper } from "../../../../mappers/token-api-payload/hotp-token-api-payload.mapper";
import { MockSystemService, MockTokenService } from "../../../../../testing/mock-services";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import { SystemService } from "../../../../services/system/system.service";
import { HOTP_HASHLIB, HOTP_OTP_LENGTH, TOTP_HASHLIB, TOTP_TIME_STEP } from "../../../../constants/token.constants";
import { EnrollHotpComponent } from "@components/token/token-enrollment/enroll-hotp/enroll-hotp.component";

describe("EnrollHotpComponent", () => {
  let component: EnrollHotpComponent;
  let fixture: ComponentFixture<EnrollHotpComponent>;
  let tokenService: MockTokenService;
  let authService: MockAuthService;
  let systemService: MockSystemService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollHotpComponent, BrowserAnimationsModule],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: HotpApiPayloadMapper, useValue: {} },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();
  });

  function createAndInit() {
    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;

    jest.spyOn(component.additionalFormFieldsChange, "emit");
    jest.spyOn(component.enrollmentArgsGetterChange, "emit");
    fixture.detectChanges();
  }

  it("should create", () => {
    createAndInit();
    expect(component).toBeTruthy();
  });

  it("emits additional fields and click handler on init", () => {
    createAndInit();

    expect(component.additionalFormFieldsChange.emit).toHaveBeenCalledTimes(1);
    const fieldsArg = (component.additionalFormFieldsChange.emit as jest.Mock).mock.calls[0][0];
    expect(Object.keys(fieldsArg)).toEqual(["twoStep", "generateOnServer", "otpLength", "otpKey", "hashAlgorithm"]);

    expect(component.enrollmentArgsGetterChange.emit).toHaveBeenCalledWith(component.enrollmentArgsGetter);
  });

  it("Check default values are set correctly on init", () => {
    createAndInit();

    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
    expect(component.otpLengthFormControl.value).toBe(6);
    expect(component.otpLengthFormControl.disabled).toBe(false);
    expect(component.hashAlgorithmFormControl.value).toBe("sha1");
    expect(component.hashAlgorithmFormControl.disabled).toBe(false);
  });

  it("Default values are also set correctly if config contains empty strings", () => {
    createAndInit();
    const mockConfig = { [HOTP_HASHLIB]: "" };
    systemService.systemConfig.set(mockConfig);

    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
    expect(component.otpLengthFormControl.value).toBe(6);
    expect(component.otpLengthFormControl.disabled).toBe(false);
    expect(component.hashAlgorithmFormControl.value).toBe("sha1");
    expect(component.hashAlgorithmFormControl.disabled).toBe(false);
  });

  it("Default values from system config are used", () => {
    createAndInit();
    const mockConfig = {
      [TOTP_HASHLIB]: "sha256",
      [TOTP_TIME_STEP]: "60",
      [HOTP_HASHLIB]: "sha512"
    };
    systemService.systemConfig.set(mockConfig);

    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.hashAlgorithmFormControl.value).toBe("sha512");
    expect(component.hashAlgorithmFormControl.disabled).toBe(false);
  });

  it("Uses policy values for hashlib and otplen over system config defaults", () => {
    createAndInit();
    const mockConfig = {
      "hotp.hashlib": "sha512"
    };
    systemService.systemConfig.set(mockConfig);
    authService.rightsWithValues.set({ [HOTP_HASHLIB]: "sha256", [HOTP_OTP_LENGTH]: "8" });
    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    function checkPolicyEnforcedValues() {
      expect(component.hashAlgorithmFormControl.value).toBe("sha256");
      expect(component.hashAlgorithmFormControl.disabled).toBe(true);
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

  it("disables generateOnServer when policy forces server-side key generation", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(true);
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.generateOnServerFormControl.disabled).toBe(true);

    component.generateOnServerFormControl.setValue(false);
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("toggles otpKey enablement & validators when generateOnServer changes", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(false);
    createAndInit();

    expect(component.otpKeyFormControl.disabled).toBe(true);

    component.generateOnServerFormControl.setValue(false);
    expect(component.otpKeyFormControl.enabled).toBe(true);

    component.otpKeyFormControl.setValue("");
    component.otpKeyFormControl.markAsTouched();
    expect(component.otpKeyFormControl.invalid).toBe(true);

    component.generateOnServerFormControl.setValue(true);
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("disables 2step control if policy hotp_2step is set to force", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("force");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    // 2-step checkbox should be present
    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector(
      'mat-checkbox[formcontrolname="twoStepControl"]'
    );
    expect(twoStepCheckbox).toBeDefined();

    expect(component.twoStepControl.value).toBe(true);
    expect(component.twoStepControl.disabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(true);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("enable 2step control if policy hotp_2step is set to allow", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("allow");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    // 2-step checkbox should be present
    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector(
      'mat-checkbox[formcontrolname="twoStepControl"]'
    );
    expect(twoStepCheckbox).toBeDefined();

    expect(component.twoStepControl.value).toBe(false);
    expect(component.twoStepControl.enabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.enabled).toBe(true);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("selecting 2 step should select and disable generate on server input", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("allow");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

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
  });

  it("hide 2step input if policy hotp_2step is disabled", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("disabled");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    // 2-step checkbox should NOT be present
    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector(
      'mat-checkbox[formcontrolname="twoStepControl"]'
    );
    expect(twoStepCheckbox).toBeNull();

    expect(component.twoStepControl.value).toBe(false);
    expect(component.twoStepControl.enabled).toBe(true);
    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.enabled).toBe(true);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("calls enrollToken with server-generated key (default values respected)", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(false);
    createAndInit();

    component.generateOnServerFormControl.setValue(true);
    component.otpLengthFormControl.setValue(8);
    component.hashAlgorithmFormControl.setValue("sha256");

    const basic = { realm: "r", username: "u" } as any;
    const args = component.enrollmentArgsGetter(basic);
    expect(args).not.toBeNull();
    expect(args!.data).toEqual(
      expect.objectContaining({
        ...basic,
        type: "hotp",
        generateOnServer: true,
        otpLength: 8,
        hashAlgorithm: "sha256"
      })
    );
    expect(args!.mapper).toBe(TestBed.inject(HotpApiPayloadMapper));
  });

  it("calls enrollToken with user-provided otpKey (trimmed) when not generating on server", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(false);
    createAndInit();

    component.generateOnServerFormControl.setValue(false);
    component.otpKeyFormControl.setValue("  ABC123  ");

    const basic = { foo: "bar" } as any;
    const args = component.enrollmentArgsGetter(basic);
    expect(args).not.toBeNull();
    expect(args!.data).toEqual(
      expect.objectContaining({
        type: "hotp",
        generateOnServer: false,
        otpKey: "ABC123"
      })
    );
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      createAndInit();
      fixture.componentRef.setInput("enrollmentData", {
        type: "hotp",
        generateOnServer: false,
        otpLength: 8,
        hashAlgorithm: "sha512"
      });
      component.ngOnInit();
      expect(component.generateOnServerFormControl.value).toBe(false);
      expect(component.otpLengthFormControl.value).toBe(8);
      expect(component.hashAlgorithmFormControl.value).toBe("sha512");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      createAndInit();
      fixture.componentRef.setInput("enrollmentData", {
        type: "hotp",
        generateOnServer: undefined,
        otpLength: undefined,
        hashAlgorithm: undefined
      });
      component.ngOnInit();
      expect(component.generateOnServerFormControl.value).toBe(true);
      expect(component.otpLengthFormControl.value).toBe(6);
      expect(component.hashAlgorithmFormControl.value).toBe("sha1");
    });
  });
});
