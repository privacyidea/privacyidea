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
import { of } from "rxjs";

import { TokenService } from "../../../../services/token/token.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { HotpApiPayloadMapper } from "../../../../mappers/token-api-payload/hotp-token-api-payload.mapper";

class MockTokenService {
  enrollToken = jest.fn().mockReturnValue(of({} as any));
}

class MockAuthService {
  checkForceServerGenerateOTPKey = jest.fn().mockReturnValue(false);
}

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
    expect(Object.keys(fieldsArg)).toEqual(["generateOnServer", "otpLength", "otpKey", "hashAlgorithm"]);

    expect(component.enrollmentArgsGetterChange.emit).toHaveBeenCalledWith(component.enrollmentArgsGetter);
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
});
