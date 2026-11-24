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
import { DAYPASSWORD_HASHLIB, DAYPASSWORD_TIME_STEP, TOTP_HASHLIB, TOTP_TIME_STEP } from "@constants/token.constants";
import { AuthService } from "@services/auth/auth.service";
import { SystemService } from "@services/system/system.service";
import { EnrollmentPolicies, EnrollmentPolicyState, TokenService } from "@services/token/token.service";
import { MockSystemService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { EnrollDaypasswordComponent } from "./enroll-daypassword.component";
import {
  clearOverlays,
  clickCheckbox,
  flushFixture,
  matSelectAt,
  pickOption,
  typeInto
} from "@testing/enroll-form-dom";
import { axe } from "@testing/axe";

function loadedPolicies(policies: Partial<EnrollmentPolicies> = {}): EnrollmentPolicyState {
  return {
    state: "loaded",
    policies: {
      defaults: {},
      "2step": null,
      force_server_generate: false,
      sms_gateways: [],
      require_description: false,
      ...policies
    }
  };
}

describe("EnrollDaypasswordComponent", () => {
  let component: EnrollDaypasswordComponent;
  let fixture: ComponentFixture<EnrollDaypasswordComponent>;
  let systemService: MockSystemService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollDaypasswordComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;

    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("Check default values are set correctly on init", () => {
    expect(component.generateOnServer()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
    expect(component.otpKey()).toEqual("");
    expect(component.otpLength()).toBe(6);
    expect(component.otpLengthForm().disabled()).toBe(false);
    expect(component.hashAlgorithm()).toBe("sha1");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.timeStep()).toBe("24h");
    expect(component.timeStepForm().disabled()).toBe(false);
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

    expect(component.generateOnServer()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(true);
    expect(component.otpKey()).toEqual("");
    expect(component.otpLength()).toBe(6);
    expect(component.otpLengthForm().disabled()).toBe(false);
    expect(component.hashAlgorithm()).toBe("sha1");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.timeStep()).toBe("24h");
    expect(component.timeStepForm().disabled()).toBe(false);
  });

  it("Default values from system config are used", () => {
    const mockConfig = {
      [TOTP_HASHLIB]: "sha256",
      [TOTP_TIME_STEP]: "60",
      [DAYPASSWORD_HASHLIB]: "sha512",
      [DAYPASSWORD_TIME_STEP]: "12h"
    };
    systemService.systemConfig.set(mockConfig);
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.hashAlgorithm()).toBe("sha512");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.timeStep()).toBe("12h");
    expect(component.timeStepForm().disabled()).toBe(false);
  });

  it("Uses policy values for hashlib, otplen, and time step over system config defaults", () => {
    const mockConfig = {
      [DAYPASSWORD_HASHLIB]: "sha512",
      [DAYPASSWORD_TIME_STEP]: "12h"
    };
    systemService.systemConfig.set(mockConfig);
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput(
      "enrollmentPolicies",
      loadedPolicies({ defaults: { hashlib: "sha256", otplen: "8", timeStep: "48h" } })
    );
    fixture.detectChanges();

    function checkPolicyEnforcedValues() {
      expect(component.hashAlgorithm()).toBe("sha256");
      expect(component.hashAlgorithmForm().disabled()).toBe(true);
      expect(component.timeStep()).toBe("48h");
      expect(component.timeStepForm().disabled()).toBe(true);
      expect(component.otpLength()).toBe(8);
      expect(component.otpLengthForm().disabled()).toBe(true);
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

  it("keeps time step, OTP length and hash algorithm in one row when the OTP key is disabled", () => {
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ force_server_generate: true }));
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    const fields: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll("mat-form-field"));
    const timeStepField = fields.find((f) => f.querySelector("mat-label")?.textContent?.trim() === "Timestep")!;
    const row = timeStepField.closest(".flex-row") as HTMLElement;
    const labels = Array.from(row.querySelectorAll("mat-form-field mat-label")).map((l) => l.textContent?.trim());
    expect(labels).toEqual(["OTP Key", "OTP Length", "Hash Algorithm", "Timestep"]);
  });

  it("keeps the OTP key in the same row as the other fields when it is shown", () => {
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    component.generateOnServer.set(false);
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    const fields: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll("mat-form-field"));
    const timeStepField = fields.find((f) => f.querySelector("mat-label")?.textContent?.trim() === "Timestep")!;
    const row = timeStepField.closest(".flex-row") as HTMLElement;
    const labels = Array.from(row.querySelectorAll("mat-form-field mat-label")).map((l) => l.textContent?.trim());
    expect(labels).toEqual(["OTP Key", "OTP Length", "Hash Algorithm", "Timestep"]);
  });

  it("presets and locks from the enrollment policies", () => {
    systemService.systemConfig.set({ [DAYPASSWORD_HASHLIB]: "sha512", [DAYPASSWORD_TIME_STEP]: "12h" });
    fixture = TestBed.createComponent(EnrollDaypasswordComponent);
    component = fixture.componentInstance;
    const generateOnServerCheckbox = () =>
      fixture.nativeElement.querySelector("mat-checkbox input[type='checkbox']") as HTMLInputElement;
    const otpKeyInput = () => fixture.nativeElement.querySelector("input[placeholder='Enter OTP key']");

    fixture.componentRef.setInput(
      "enrollmentPolicies",
      loadedPolicies({
        defaults: { hashlib: "sha256", otplen: "8", timeStep: "2h" },
        force_server_generate: true
      })
    );
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.hashAlgorithm()).toBe("sha256");
    expect(component.hashAlgorithmForm().disabled()).toBe(true);
    expect(component.otpLength()).toBe(8);
    expect(component.otpLengthForm().disabled()).toBe(true);
    expect(component.timeStep()).toBe("2h");
    expect(component.timeStepForm().disabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(generateOnServerCheckbox().disabled).toBe(true);
    expect(otpKeyInput()).not.toBeNull();
    expect(otpKeyInput().disabled).toBe(true);

    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies());
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.hashAlgorithm()).toBe("sha512");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.otpLength()).toBe(6);
    expect(component.otpLengthForm().disabled()).toBe(false);
    expect(component.timeStep()).toBe("12h");
    expect(component.timeStepForm().disabled()).toBe(false);
    expect(generateOnServerCheckbox().disabled).toBe(false);
    expect(otpKeyInput()).not.toBeNull();
    expect(otpKeyInput().disabled).toBe(true);
    component.generateOnServer.set(false);
    fixture.detectChanges();
    expect(otpKeyInput()).not.toBeNull();

    fixture.componentRef.setInput("enrollmentPolicies", { state: "pending" });
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.hashAlgorithmForm().disabled()).toBe(true);
    expect(component.otpLengthForm().disabled()).toBe(true);
    expect(component.timeStepForm().disabled()).toBe(true);
    expect(generateOnServerCheckbox().disabled).toBe(true);
  });

  it("keeps the policy values over the enrollment data", () => {
    fixture.componentRef.setInput("enrollmentData", {
      type: "daypassword",
      otpLength: 6,
      hashAlgorithm: "sha1",
      timeStep: "24h"
    });
    fixture.componentRef.setInput(
      "enrollmentPolicies",
      loadedPolicies({ defaults: { hashlib: "sha256", otplen: "8", timeStep: "2h" } })
    );
    fixture.detectChanges();
    TestBed.tick();

    expect(component.hashAlgorithm()).toBe("sha256");
    expect(component.otpLength()).toBe(8);
    expect(component.timeStep()).toBe("2h");
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
      fixture.detectChanges();
      expect(component.otpKey()).toBe("otp-key-123");
      expect(component.otpLength()).toBe(8);
      expect(component.hashAlgorithm()).toBe("SHA512");
      expect(component.timeStep()).toBe("12h");
      expect(component.generateOnServer()).toBe(false);
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
      fixture.detectChanges();
      expect(component.otpKey()).toBe("");
      expect(component.otpLength()).toBe(6);
      expect(component.hashAlgorithm()).toBe("sha256");
      expect(component.timeStep()).toBe("24h");
      expect(component.generateOnServer()).toBe(true);
    });
  });

  describe("key input visibility", () => {
    const keyInput = () => fixture.nativeElement.querySelector("input[placeholder='Enter OTP key']");
    const checkbox = () =>
      fixture.nativeElement.querySelector("mat-checkbox input[type='checkbox']") as HTMLInputElement;
    const settle = () => {
      fixture.detectChanges();
      TestBed.tick();
      fixture.detectChanges();
    };

    it("keeps the key input disabled while generate on server is ticked and enabled when unticked", () => {
      settle();
      expect(component.generateOnServer()).toBe(true);
      expect(keyInput()).not.toBeNull();
      expect(keyInput().disabled).toBe(true);

      checkbox().click();
      settle();
      expect(component.generateOnServer()).toBe(false);
      expect(keyInput().disabled).toBe(false);

      checkbox().click();
      settle();
      expect(component.generateOnServer()).toBe(true);
      expect(keyInput().disabled).toBe(true);
    });

    it("keeps the key input disabled when the policy forces server generation", () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ force_server_generate: true }));
      settle();
      expect(component.generateOnServer()).toBe(true);
      expect(checkbox().disabled).toBe(true);
      expect(keyInput()).not.toBeNull();
      expect(keyInput().disabled).toBe(true);
    });

    it("keeps Enroll disabled while the visible key is empty", () => {
      settle();
      expect(component.fieldsInvalid()).toBe(false);

      component.generateOnServer.set(false);
      settle();
      expect(component.fieldsInvalid()).toBe(true);

      component.otpKey.set("12345678901234567890123456789012");
      settle();
      expect(component.fieldsInvalid()).toBe(false);
    });

    it("does not render the key input in wizard mode", () => {
      fixture.componentRef.setInput("wizard", true);
      settle();
      expect(keyInput()).toBeNull();
    });
  });

  describe("bound controls", () => {
    afterEach(clearOverlays);

    it("writes a click on the generate checkbox to the model and marks the field dirty", async () => {
      expect(component.generateOnServerForm().dirty()).toBe(false);

      await clickCheckbox(fixture);

      expect(component.generateOnServer()).toBe(false);
      expect(component.generateOnServerForm().dirty()).toBe(true);
    });

    it("writes the picked OTP length and hash algorithm to the model", async () => {
      await pickOption(fixture, matSelectAt(fixture, 0), 1);
      await pickOption(fixture, matSelectAt(fixture, 1), 2);

      expect(component.otpLength()).toBe(8);
      expect(component.otpLengthForm().dirty()).toBe(true);
      expect(component.hashAlgorithm()).toBe("sha512");
      expect(component.hashAlgorithmForm().dirty()).toBe(true);
    });

    it("renders the OTP key errors once the field was touched", async () => {
      component.generateOnServer.set(false);
      await flushFixture(fixture);

      fixture.nativeElement.querySelector("input[matInput]").dispatchEvent(new Event("blur"));
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("OTP key is required");
      expect(fixture.nativeElement.textContent).toContain("OTP key must be at least 16 characters long.");
    });

    it("accepts a typed OTP key of at least 16 characters", async () => {
      component.generateOnServer.set(false);
      await flushFixture(fixture);

      await typeInto(fixture, fixture.nativeElement.querySelector("input[matInput]"), "0123456789abcdef");

      expect(component.otpKeyForm().valid()).toBe(true);
      expect(fixture.nativeElement.querySelector("mat-error")).toBeNull();
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
