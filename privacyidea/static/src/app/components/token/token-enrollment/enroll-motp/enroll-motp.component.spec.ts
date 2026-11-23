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
import { ValidationError } from "@angular/forms/signals";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { MotpEnrollmentData } from "@app/mappers/token-api-payload/motp-token-api-payload.mapper";
import { EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import { EnrollMotpComponent } from "./enroll-motp.component";
import { EnrollmentPolicies, EnrollmentPolicyState, TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";

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

describe("EnrollMotpComponent", () => {
  let component: EnrollMotpComponent;
  let fixture: ComponentFixture<EnrollMotpComponent>;

  const basicOptions: TokenEnrollmentData = {
    type: "motp",
    description: "",
    containerSerial: "",
    validityPeriodStart: "",
    validityPeriodEnd: "",
    pin: ""
  } as TokenEnrollmentData;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollMotpComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollMotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should register itself as the EnrollTokenBase for this token type", () => {
    expect(fixture.debugElement.injector.get(EnrollTokenBase)).toBe(component);
  });

  it("should initially have generateOnServer true and otpKey form disabled", () => {
    expect(component.generateOnServer()).toBe(true);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  it("locks generate on server when forced", () => {
    const generateOnServerCheckbox = () =>
      fixture.nativeElement.querySelector("mat-checkbox input[type='checkbox']") as HTMLInputElement;
    const keyInput = () => fixture.nativeElement.querySelector("input[placeholder='Enter OTP key']");
    component.generateOnServer.set(false);

    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ force_server_generate: true }));
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(component.generateOnServer()).toBe(true);
    expect(generateOnServerCheckbox().disabled).toBe(true);
    expect(keyInput()).not.toBeNull();
    expect(keyInput().disabled).toBe(true);

    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies());
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(generateOnServerCheckbox().disabled).toBe(false);
    expect(keyInput()).not.toBeNull();
    expect(keyInput().disabled).toBe(true);
    component.generateOnServer.set(false);
    fixture.detectChanges();
    expect(keyInput()).not.toBeNull();

    fixture.componentRef.setInput("enrollmentPolicies", { state: "pending" });
    fixture.detectChanges();
    TestBed.tick();
    fixture.detectChanges();

    expect(generateOnServerCheckbox().disabled).toBe(true);
  });

  describe("motpPinForm validation", () => {
    it("should require motpPin", () => {
      expect(
        component
          .motpPinForm()
          .errors()
          .some((e: ValidationError) => e.kind === "required")
      ).toBe(true);
    });

    it("should reject pin shorter than 4 chars", () => {
      component.motpPin.set("abc");
      expect(
        component
          .motpPinForm()
          .errors()
          .some((e: ValidationError) => e.kind === "minlength")
      ).toBe(true);
    });

    it("should accept pin of 4 chars or longer", () => {
      component.motpPin.set("abcd");
      expect(
        component
          .motpPinForm()
          .errors()
          .some((e: ValidationError) => e.kind === "minlength")
      ).toBe(false);
    });
  });

  describe("repeatMotpPinForm validation", () => {
    it("should fail when repeat differs from motpPin", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abce");
      expect(
        component
          .repeatMotpPinForm()
          .errors()
          .some((e: ValidationError) => e.kind === "motpPinMismatch")
      ).toBe(true);
    });

    it("should pass when repeat matches motpPin", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abcd");
      expect(
        component
          .repeatMotpPinForm()
          .errors()
          .some((e: ValidationError) => e.kind === "motpPinMismatch")
      ).toBe(false);
    });
  });

  describe("motpPinError", () => {
    it("should stay empty while the field is untouched", () => {
      component.motpPin.set("");
      expect(component.motpPinError()).toBe("");
    });

    it("should report the required error once touched", () => {
      component.motpPin.set("");
      component.motpPinForm().markAsTouched();
      expect(component.motpPinError()).toBe("Password is required");
    });

    it("should report the minlength error once touched", () => {
      component.motpPin.set("abc");
      component.motpPinForm().markAsTouched();
      expect(component.motpPinError()).toBe("Password must be at least 4 characters long");
    });

    it("should be empty for a valid touched pin", () => {
      component.motpPin.set("abcd");
      component.motpPinForm().markAsTouched();
      expect(component.motpPinError()).toBe("");
    });
  });

  describe("repeatMotpPinError", () => {
    it("should stay empty while the field is untouched", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abce");
      expect(component.repeatMotpPinError()).toBe("");
    });

    it("should report the mismatch once touched", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abce");
      component.repeatMotpPinForm().markAsTouched();
      expect(component.repeatMotpPinError()).toBe("mOTP PINs do not match.");
    });

    it("should be empty when the pins match", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abcd");
      component.repeatMotpPinForm().markAsTouched();
      expect(component.repeatMotpPinError()).toBe("");
    });
  });

  describe("buildEnrollmentArgs", () => {
    it("should return null and mark touched when motpPin is invalid", () => {
      component.motpPin.set("");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.motpPinForm().touched()).toBe(true);
    });

    it("should return null and mark touched when repeat pin does not match", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("xyzw");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.repeatMotpPinForm().touched()).toBe(true);
    });

    it("should return null and mark otpKey touched when generateOnServer is false and otpKey is empty", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abcd");
      component.generateOnServer.set(false);
      component.otpKey.set("");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.otpKeyForm().touched()).toBe(true);
    });

    it("should return data without otpKey when generateOnServer is true", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abcd");
      component.generateOnServer.set(true);
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.type).toBe("motp");
      expect(result!.data.generateOnServer).toBe(true);
      expect(result!.data.motpPin).toBe("abcd");
      expect((result!.data as MotpEnrollmentData).otpKey).toBeUndefined();
    });

    it("should include otpKey when generateOnServer is false", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abcd");
      component.generateOnServer.set(false);
      component.otpKey.set("ABCDEF");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect((result!.data as MotpEnrollmentData).otpKey).toBe("ABCDEF");
      expect(result!.data.generateOnServer).toBe(false);
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
});
