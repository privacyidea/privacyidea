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
import { DEFAULT_OTP_LENGTH, TOTP_HASHLIB, TOTP_TIME_STEP } from "@constants/token.constants";
import { AuthService } from "@services/auth/auth.service";
import { SystemService } from "@services/system/system.service";
import { EnrollmentPolicies, EnrollmentPolicyState, TokenService } from "@services/token/token.service";
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

/** The native input of the `mat-checkbox` whose label contains `text`. */
function checkboxInputByText(fixture: ComponentFixture<unknown>, text: string): HTMLInputElement {
  return Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("mat-checkbox"))
    .find((box) => box.textContent?.includes(text))
    ?.querySelector("input[type='checkbox']") as HTMLInputElement;
}

describe("EnrollTotpComponent", () => {
  let component: EnrollTotpComponent;
  let fixture: ComponentFixture<EnrollTotpComponent>;
  let systemService: MockSystemService;

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

    systemService = TestBed.inject(SystemService) as unknown as MockSystemService;

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
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput(
      "enrollmentPolicies",
      loadedPolicies({ defaults: { hashlib: "sha512", otplen: "8", timeStep: "45" } })
    );
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

  it("presets hashlib, otplen and time step from the system config", () => {
    systemService.systemConfig.set({ [TOTP_HASHLIB]: "sha256", [TOTP_TIME_STEP]: "60", [DEFAULT_OTP_LENGTH]: "8" });
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.hashAlgorithm()).toBe("sha256");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.timeStep()).toBe(60);
    expect(component.timeStepForm().disabled()).toBe(false);
    expect(component.otpLength()).toBe(8);
    expect(component.otpLengthForm().disabled()).toBe(false);
  });

  describe("a choice that a locking policy overrode", () => {
    const pick = () => {
      fixture.detectChanges();
      component.hashAlgorithm.set("sha256");
      component.hashAlgorithmForm().markAsDirty();
      component.otpLength.set(8);
      component.otpLengthForm().markAsDirty();
      TestBed.tick();
    };
    const loadPolicies = (state: EnrollmentPolicyState) => {
      fixture.componentRef.setInput("enrollmentPolicies", state);
      fixture.detectChanges();
      TestBed.tick();
    };

    it("is not restored when the policy no longer locks the field", () => {
      pick();
      loadPolicies(loadedPolicies({ defaults: { hashlib: "sha512", otplen: "6" } }));
      expect(component.hashAlgorithm()).toBe("sha512");
      expect(component.otpLength()).toBe(6);

      loadPolicies(loadedPolicies());

      expect(component.hashAlgorithm()).toBe("sha1");
      expect(component.otpLength()).toBe(6);
    });

  });

  it("keeps the values the user picked when the system config loads later", () => {
    fixture.detectChanges();
    component.hashAlgorithm.set("sha512");
    component.timeStep.set(60);
    component.otpLength.set(8);
    // Every preset must change, otherwise the linked signals do not recompute at all.
    systemService.systemConfig.set({ [TOTP_HASHLIB]: "sha256", [TOTP_TIME_STEP]: "90", [DEFAULT_OTP_LENGTH]: "10" });
    fixture.detectChanges();

    expect(component.hashAlgorithm()).toBe("sha512");
    expect(component.timeStep()).toBe(60);
    expect(component.otpLength()).toBe(8);
  });

  it("keeps the presets when enrollment data without these values arrives later", () => {
    systemService.systemConfig.set({ [TOTP_HASHLIB]: "sha512", [TOTP_TIME_STEP]: "60", [DEFAULT_OTP_LENGTH]: "8" });
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    fixture.componentRef.setInput("enrollmentData", { type: "totp", description: "live-check-rollover" });
    fixture.detectChanges();

    expect(component.hashAlgorithm()).toBe("sha512");
    expect(component.timeStep()).toBe(60);
    expect(component.otpLength()).toBe(8);
    expect(component.generateOnServer()).toBe(true);
  });

  it("applies the values the enrollment data contains", () => {
    fixture.componentRef.setInput("enrollmentData", {
      type: "totp",
      generateOnServer: false,
      otpLength: 8,
      hashAlgorithm: "sha256",
      timeStep: 60
    });
    fixture.detectChanges();

    expect(component.generateOnServer()).toBe(false);
    expect(component.hashAlgorithm()).toBe("sha256");
    expect(component.timeStep()).toBe(60);
    expect(component.otpLength()).toBe(8);
  });

  it("keeps enrollment data values that equal the preset when the system config loads later", () => {
    fixture.componentRef.setInput("enrollmentData", {
      type: "totp",
      otpLength: 6,
      hashAlgorithm: "sha1",
      timeStep: 30
    });
    fixture.detectChanges();
    expect(component.otpLength()).toBe(6);
    expect(component.hashAlgorithm()).toBe("sha1");
    expect(component.timeStep()).toBe(30);

    systemService.systemConfig.set({ [TOTP_HASHLIB]: "sha256", [TOTP_TIME_STEP]: "60", [DEFAULT_OTP_LENGTH]: "8" });
    fixture.detectChanges();

    expect(component.otpLength()).toBe(6);
    expect(component.hashAlgorithm()).toBe("sha1");
    expect(component.timeStep()).toBe(30);
  });

  it("keeps the policy values over a system config that loads later", () => {
    fixture.componentRef.setInput(
      "enrollmentPolicies",
      loadedPolicies({ defaults: { hashlib: "sha512", otplen: "6", timeStep: "30" } })
    );
    fixture.detectChanges();
    systemService.systemConfig.set({ [TOTP_HASHLIB]: "sha256", [TOTP_TIME_STEP]: "60", [DEFAULT_OTP_LENGTH]: "8" });
    fixture.detectChanges();

    expect(component.hashAlgorithm()).toBe("sha512");
    expect(component.timeStep()).toBe(30);
    expect(component.otpLength()).toBe(6);
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
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ force_server_generate: true }));
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
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ "2step": "force" }));
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
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ "2step": "allow" }));
    fixture.detectChanges();

    expect(component.twoStepEnabled()).toBe(false);
    expect(component.twoStepDisabled()).toBe(false);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("selecting 2 step should select and disable generate on server input", () => {
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ "2step": "allow" }));
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
    fixture = TestBed.createComponent(EnrollTotpComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies());
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

  it("keeps time step, OTP length and hash algorithm in one row when the OTP key is disabled", () => {
    fixture = TestBed.createComponent(EnrollTotpComponent);
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
    fixture = TestBed.createComponent(EnrollTotpComponent);
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
    const otpKeyInput = () => fixture.nativeElement.querySelector("input[placeholder='Enter OTP key']");

    fixture.componentRef.setInput(
      "enrollmentPolicies",
      loadedPolicies({
        defaults: { hashlib: "sha512", otplen: "8", timeStep: "60" },
        "2step": "force",
        force_server_generate: true
      })
    );
    fixture.detectChanges();
    TestBed.tick();

    expect(component.hashAlgorithm()).toBe("sha512");
    expect(component.hashAlgorithmForm().disabled()).toBe(true);
    expect(component.otpLength()).toBe(8);
    expect(component.otpLengthForm().disabled()).toBe(true);
    expect(component.timeStep()).toBe(60);
    expect(component.timeStepForm().disabled()).toBe(true);
    expect(component.twoStep()).toBe("force");
    expect(component.twoStepEnabled()).toBe(true);
    expect(component.twoStepDisabled()).toBe(true);
    expect(component.generateOnServer()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
    expect(otpKeyInput()).not.toBeNull();
    expect(otpKeyInput().disabled).toBe(true);

    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies());
    fixture.detectChanges();
    TestBed.tick();

    expect(component.hashAlgorithm()).toBe("sha1");
    expect(component.hashAlgorithmForm().disabled()).toBe(false);
    expect(component.otpLength()).toBe(6);
    expect(component.otpLengthForm().disabled()).toBe(false);
    expect(component.timeStep()).toBe(30);
    expect(component.timeStepForm().disabled()).toBe(false);
    expect(component.twoStep()).toBe("disabled");
    expect(component.twoStepEnabled()).toBe(false);
    expect(component.generateOnServerDisabled()).toBe(false);
    expect(otpKeyInput()).not.toBeNull();
    expect(otpKeyInput().disabled).toBe(true);
    component.generateOnServer.set(false);
    fixture.detectChanges();
    expect(otpKeyInput()).not.toBeNull();

    fixture.componentRef.setInput("enrollmentPolicies", { state: "pending" });
    fixture.detectChanges();
    TestBed.tick();

    expect(component.hashAlgorithmForm().disabled()).toBe(true);
    expect(component.otpLengthForm().disabled()).toBe(true);
    expect(component.timeStepForm().disabled()).toBe(true);
    expect(component.generateOnServerDisabled()).toBe(true);
  });

  it("keeps the policy values over the enrollment data", () => {
    fixture.componentRef.setInput("enrollmentData", {
      type: "totp",
      otpLength: 6,
      hashAlgorithm: "sha1",
      timeStep: 30
    });
    fixture.componentRef.setInput(
      "enrollmentPolicies",
      loadedPolicies({ defaults: { hashlib: "sha512", otplen: "8", timeStep: "60" } })
    );
    fixture.detectChanges();
    TestBed.tick();

    expect(component.hashAlgorithm()).toBe("sha512");
    expect(component.otpLength()).toBe(8);
    expect(component.timeStep()).toBe(60);
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

  describe("key input visibility", () => {
    const keyInput = () => fixture.nativeElement.querySelector("input[placeholder='Enter OTP key']");
    const checkbox = () => checkboxInputByText(fixture, "Generate the OTP key");
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

      checkboxInputByText(fixture, "Generate the OTP key").click();
      await flushFixture(fixture);

      expect(component.generateOnServer()).toBe(false);
      expect(component.generateOnServerForm().dirty()).toBe(true);
    });

    it("writes a click on the two-step checkbox to the model", async () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ "2step": "allow" }));
      await flushFixture(fixture);

      await clickCheckbox(fixture, "mat-checkbox:first-of-type");

      expect(component.twoStepEnabled()).toBe(true);
      expect(component.twoStepEnabledForm().dirty()).toBe(true);
    });

    it("renders the checkboxes disabled while the policy forces the setting", async () => {
      fixture.componentRef.setInput(
        "enrollmentPolicies",
        loadedPolicies({ "2step": "force", force_server_generate: true })
      );
      await flushFixture(fixture);

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

    it("keeps a value the user picked that equals the preset when the system config loads later", async () => {
      // Picking the already selected option emits no change, so the user switches away and back to the preset.
      await pickOption(fixture, matSelectAt(fixture, 0), 1);
      await pickOption(fixture, matSelectAt(fixture, 0), 0);
      await pickOption(fixture, matSelectAt(fixture, 1), 2);
      await pickOption(fixture, matSelectAt(fixture, 1), 0);
      await pickOption(fixture, matSelectAt(fixture, 2), 1);
      await pickOption(fixture, matSelectAt(fixture, 2), 0);
      expect(component.otpLength()).toBe(6);
      expect(component.otpLengthForm().dirty()).toBe(true);
      expect(component.hashAlgorithm()).toBe("sha1");
      expect(component.hashAlgorithmForm().dirty()).toBe(true);
      expect(component.timeStep()).toBe(30);
      expect(component.timeStepForm().dirty()).toBe(true);

      systemService.systemConfig.set({ [TOTP_HASHLIB]: "sha256", [TOTP_TIME_STEP]: "60", [DEFAULT_OTP_LENGTH]: "8" });
      await flushFixture(fixture);

      expect(component.otpLength()).toBe(6);
      expect(component.hashAlgorithm()).toBe("sha1");
      expect(component.timeStep()).toBe(30);
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

  describe("two-step checkbox without a policy target (template editor)", () => {
    afterEach(clearOverlays);

    const twoStepElement = () =>
      Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("mat-checkbox")).find((box) =>
        box.textContent?.includes("two-step")
      );
    const twoStepBox = () =>
      twoStepElement()?.querySelector<HTMLInputElement>('input[type="checkbox"]') as HTMLInputElement;

    async function render(data: Record<string, unknown> | null, policies: EnrollmentPolicyState) {
      fixture = TestBed.createComponent(EnrollTotpComponent);
      component = fixture.componentInstance;
      if (data) fixture.componentRef.setInput("enrollmentData", data);
      fixture.componentRef.setInput("enrollmentPolicies", policies);
      await flushFixture(fixture);
    }

    it("shows the stored twoStepInit checked and emits it", async () => {
      await render({ type: "totp", twoStepInit: true }, { state: "unrestricted" });

      expect(twoStepElement()).toBeDefined();
      expect(twoStepBox().checked).toBe(true);
      expect(twoStepBox().disabled).toBe(false);
      expect(component.generateOnServerDisabled()).toBe(true);
      expect(component.buildEnrollmentArgs({ type: "totp" })!.data).toEqual(
        expect.objectContaining({ twoStepInit: true, generateOnServer: true })
      );
    });

    it("shows the checkbox unchecked without twoStepInit and lets the admin toggle it", async () => {
      await render({ type: "totp" }, { state: "unrestricted" });

      expect(twoStepElement()).toBeDefined();
      expect(twoStepBox().checked).toBe(false);

      twoStepBox().click();
      await flushFixture(fixture);

      expect(component.twoStepEnabled()).toBe(true);
      expect(component.buildEnrollmentArgs({ type: "totp" })!.data).toEqual(
        expect.objectContaining({ twoStepInit: true })
      );
    });

    it("disables the checkbox for a disabled form", async () => {
      await render(null, { state: "unrestricted" });
      fixture.componentRef.setInput("disabled", true);
      await flushFixture(fixture);

      expect(twoStepElement()).toBeDefined();
      expect(twoStepBox().disabled).toBe(true);
    });

    it("keeps the checkbox hidden for loaded policies without 2step", async () => {
      await render(null, loadedPolicies({ "2step": null }));

      expect(twoStepElement()).toBeUndefined();
    });
  });
});
