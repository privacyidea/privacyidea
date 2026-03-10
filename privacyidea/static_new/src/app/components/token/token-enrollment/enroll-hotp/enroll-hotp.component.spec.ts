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
import { EnrollHotpComponent } from "./enroll-hotp.component";

import { TokenService } from "../../../../services/token/token.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { HotpApiPayloadMapper } from "../../../../mappers/token-api-payload/hotp-token-api-payload.mapper";
import { MockTokenService } from "../../../../../testing/mock-services";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";


describe("EnrollHotpComponent", () => {
  let component: EnrollHotpComponent;
  let fixture: ComponentFixture<EnrollHotpComponent>;
  let tokenService: MockTokenService;
  let authService: MockAuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollHotpComponent, BrowserAnimationsModule],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: HotpApiPayloadMapper, useValue: {} }
      ]
    }).compileComponents();
  });

  function createAndInit() {
    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
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

  it("should initially have generateOnServer enabled and otpKey disabled", () => {
    createAndInit();

    expect(component.generateOnServerFormControl.value).toBe(true);
    expect(component.generateOnServerFormControl.disabled).toBe(false);
    expect(component.otpKeyFormControl.value).toEqual("");
    expect(component.otpKeyFormControl.disabled).toBe(true);
  });

  it("disables generateOnServer when policy forces server-side key generation", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(true);
    createAndInit();
    fixture.detectChanges();
    TestBed.flushEffects();
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
    TestBed.flushEffects();
    fixture.detectChanges();

    // 2-step checkbox should be present
    const twoStepCheckbox = fixture.debugElement.nativeElement.querySelector("mat-checkbox[formcontrolname=\"twoStepControl\"]");
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
    TestBed.flushEffects();
    fixture.detectChanges();

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
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("allow");
    createAndInit();
    fixture.detectChanges();
    TestBed.flushEffects();
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
    TestBed.flushEffects();
    fixture.detectChanges();

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

  it("enrollmentArgsGetter returns null and marks controls when manual key is required but missing", (done) => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(false);
    createAndInit();

    component.generateOnServerFormControl.setValue(false);
    component.otpKeyFormControl.setValue("");

    const res = component.enrollmentArgsGetter({} as any);

    expect(res).toBeNull();
    expect(component.generateOnServerFormControl.touched).toBe(true);
    expect(component.otpLengthFormControl.touched).toBe(true);
    expect(component.hashAlgorithmFormControl.touched).toBe(true);
    expect(component.otpKeyFormControl.touched).toBe(true);
    done();
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
