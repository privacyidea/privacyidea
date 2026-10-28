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

import { HotpApiPayloadMapper } from "@app/mappers/token-api-payload/hotp-token-api-payload.mapper";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollHotpComponent } from "@components/token/token-enrollment/enroll-hotp/enroll-hotp.component";
import { HOTP_HASHLIB, HOTP_OTP_LENGTH } from "@constants/token.constants";
import { AuthService } from "@services/auth/auth.service";
import { SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import { MockSystemService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import {
  checkboxInput,
  clearOverlays,
  clickCheckbox,
  flushFixture,
  matSelectAt,
  pickOption
} from "@testing/enroll-form-dom";

describe("EnrollHotpComponent", () => {
  let component: EnrollHotpComponent;
  let fixture: ComponentFixture<EnrollHotpComponent>;
  let authService: MockAuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollHotpComponent],
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

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;

    fixture.detectChanges();
  }

  it("should create", () => {
    createAndInit();
    expect(component).toBeTruthy();
  });

  it("Check default values are set correctly on init", () => {
    createAndInit();

    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
    expect(component.otpLength()).toBe(6);
    expect(component.otpLengthForm().disabled()).toBe(false);
    expect(component.hashAlgorithm()).toBe("sha1");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
  });

  it("Uses policy values for hashlib and otplen", () => {
    createAndInit();
    authService.rightsWithValues.set({ [HOTP_HASHLIB]: "sha256", [HOTP_OTP_LENGTH]: "8" });
    fixture = TestBed.createComponent(EnrollHotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    function checkPolicyEnforcedValues() {
      expect(component.hashAlgorithm()).toBe("sha256");
      expect(component.hashAlgorithmForm().disabled()).toBe(true);
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

  it("disables generateOnServer when policy forces server-side key generation", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(true);
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("toggles otpKey enablement & validators when generateOnServer changes", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(false);
    createAndInit();

    expect(component.otpKeyForm().disabled()).toBe(true);

    component.generateOnServer.set(false);
    fixture.detectChanges();
    expect(component.otpKeyForm().disabled()).toBe(false);

    component.otpKey.set("");
    component.otpKeyForm().markAsTouched();
    fixture.detectChanges();
    expect(component.otpKeyForm().valid()).toBe(false);

    component.generateOnServer.set(true);
    fixture.detectChanges();
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("disables 2step control if policy hotp_2step is set to force", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("force");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(true);
    expect(component.twoStepDisabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("enable 2step control if policy hotp_2step is set to allow", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("allow");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(false);
    expect(component.twoStepDisabled()).toBe(false);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("selecting 2 step should select and disable generate on server input", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("allow");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
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

    // Select 2-step should select generate on server (effect kicks in)
    component.twoStepEnabled.set(true);
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("hide 2step input if policy hotp_2step is disabled", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("disabled");
    createAndInit();
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(false);
    expect(component.twoStepDisabled()).toBe(false);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("calls enrollToken with server-generated key (default values respected)", () => {
    (TestBed.inject(AuthService) as unknown as MockAuthService).checkForceServerGenerateOTPKey.mockReturnValue(false);
    createAndInit();

    component.generateOnServer.set(true);
    component.otpLength.set(8);
    component.hashAlgorithm.set("sha256");

    const basic: TokenEnrollmentData = { type: "hotp", realm: "r", username: "u" };
    const args = component.buildEnrollmentArgs(basic);
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

    component.generateOnServer.set(false);
    component.otpKey.set("  ABCDEFGHIJKLMNOP  ");
    fixture.detectChanges();

    const basic: TokenEnrollmentData = { type: "hotp", foo: "bar" };
    const args = component.buildEnrollmentArgs(basic);
    expect(args).not.toBeNull();
    expect(args!.data).toEqual(
      expect.objectContaining({
        type: "hotp",
        generateOnServer: false,
        otpKey: "ABCDEFGHIJKLMNOP"
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
      fixture.detectChanges();
      expect(component.generateOnServer()).toBe(false);
      expect(component.otpLength()).toBe(8);
      expect(component.hashAlgorithm()).toBe("sha512");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      createAndInit();
      fixture.componentRef.setInput("enrollmentData", {
        type: "hotp",
        generateOnServer: undefined,
        otpLength: undefined,
        hashAlgorithm: undefined
      });
      fixture.detectChanges();
      expect(component.generateOnServer()).toBe(true);
      expect(component.otpLength()).toBe(6);
      expect(component.hashAlgorithm()).toBe("sha1");
    });
  });

  describe("bound controls", () => {
    afterEach(clearOverlays);

    it("writes a click on the generate checkbox to the model and marks the field dirty", async () => {
      createAndInit();
      expect(component.generateOnServerForm().dirty()).toBe(false);

      await clickCheckbox(fixture, "mat-checkbox.server-checkbox");

      expect(component.generateOnServer()).toBe(false);
      expect(component.generateOnServerForm().dirty()).toBe(true);
    });

    it("writes a click on the two-step checkbox to the model", async () => {
      (TestBed.inject(AuthService) as unknown as MockAuthService).check2Step.mockReturnValue("allow");
      createAndInit();

      await clickCheckbox(fixture, "mat-checkbox:not(.server-checkbox)");

      expect(component.twoStepEnabled()).toBe(true);
      expect(component.twoStepEnabledForm().dirty()).toBe(true);
    });

    it("renders the checkboxes disabled while the policy forces the setting", () => {
      const auth = TestBed.inject(AuthService) as unknown as MockAuthService;
      auth.check2Step.mockReturnValue("force");
      auth.checkForceServerGenerateOTPKey.mockReturnValue(true);
      createAndInit();

      expect(checkboxInput(fixture, "mat-checkbox.server-checkbox").disabled).toBe(true);
      expect(checkboxInput(fixture, "mat-checkbox:not(.server-checkbox)").disabled).toBe(true);
    });

    it("writes the picked OTP length and hash algorithm to the model", async () => {
      createAndInit();

      await pickOption(fixture, matSelectAt(fixture, 0), 1);
      await pickOption(fixture, matSelectAt(fixture, 1), 2);

      expect(component.otpLength()).toBe(8);
      expect(component.otpLengthForm().dirty()).toBe(true);
      expect(component.hashAlgorithm()).toBe("sha512");
      expect(component.hashAlgorithmForm().dirty()).toBe(true);
    });

    it("renders the OTP key errors once the field was touched", async () => {
      createAndInit();
      component.generateOnServer.set(false);
      await flushFixture(fixture);
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();

      fixture.nativeElement.querySelector("input[matInput]").dispatchEvent(new Event("blur"));
      await flushFixture(fixture);

      const text = fixture.nativeElement.textContent;
      expect(text).toContain("OTP key is required");
      expect(text).toContain("OTP key must be at least 16 characters long.");
    });
  });
});
