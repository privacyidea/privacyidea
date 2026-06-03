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

describe("EnrollHotpComponent", () => {
  let component: EnrollHotpComponent;
  let fixture: ComponentFixture<EnrollHotpComponent>;
  let tokenService: MockTokenService;
  let authService: MockAuthService;
  let systemService: MockSystemService;

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

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;

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

    const basic = { realm: "r", username: "u" } as TokenEnrollmentData;
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

    const basic = { foo: "bar" } as TokenEnrollmentData;
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
});
