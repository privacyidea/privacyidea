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
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EnrollYubikeyComponent } from "./enroll-yubikey.component";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";
import { flushFixture, typeInto } from "@testing/enroll-form-dom";
import { axe } from "@testing/axe";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";

describe("EnrollYubikeyComponent", () => {
  let component: EnrollYubikeyComponent;
  let fixture: ComponentFixture<EnrollYubikeyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient(), { provide: TokenService, useClass: MockTokenService }],
      imports: [EnrollYubikeyComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollYubikeyComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("writes the pushed Yubikey OTP to the model, marks it dirty and widens the OTP length", async () => {
    const input = fixture.nativeElement.querySelector("input[matInput]") as HTMLInputElement;
    expect(component.testYubiKeyForm().dirty()).toBe(false);

    await typeInto(fixture, input, "x".repeat(40));
    TestBed.tick();

    expect(component.testYubiKey()).toBe("x".repeat(40));
    expect(component.testYubiKeyForm().dirty()).toBe(true);
    expect(component.otpLength()).toBe(40);
  });

  describe("OTP length", () => {
    const otpLengthInput = () => fixture.nativeElement.querySelectorAll("input[matInput]")[1] as HTMLInputElement;
    const testInput = () => fixture.nativeElement.querySelectorAll("input[matInput]")[0] as HTMLInputElement;

    it("keeps the default of 44 without a pushed Yubikey OTP", async () => {
      await flushFixture(fixture);

      expect(component.otpLength()).toBe(44);
      expect(otpLengthInput().value).toBe("44");
    });

    it("keeps a typed length", async () => {
      await typeInto(fixture, otpLengthInput(), "50");
      TestBed.tick();

      expect(component.otpLength()).toBe(50);
    });

    it("leaves the length as it is for test input shorter than 32 characters", async () => {
      await typeInto(fixture, otpLengthInput(), "50");
      await typeInto(fixture, testInput(), "x".repeat(31));
      TestBed.tick();

      expect(component.otpLength()).toBe(50);
    });

    it("renders only the required error for an empty OTP length", async () => {
      await typeInto(fixture, otpLengthInput(), "");
      otpLengthInput().dispatchEvent(new Event("blur"));
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("OTP length is required");
      expect(fixture.nativeElement.textContent).not.toContain("must be at least 32");
    });

    it("renders only the minimum error for an OTP length below 32", async () => {
      await typeInto(fixture, otpLengthInput(), "31");
      otpLengthInput().dispatchEvent(new Event("blur"));
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("OTP length must be at least 32.");
      expect(fixture.nativeElement.textContent).not.toContain("OTP length is required");
      expect(component.buildEnrollmentArgs({ type: "yubikey" } as TokenEnrollmentData)).toBeNull();
    });
  });

  describe("OTP key errors", () => {
    const otpKeyInput = () => fixture.nativeElement.querySelectorAll("input[matInput]")[2] as HTMLInputElement;

    it("renders only the required error for an empty OTP key once the field was touched", async () => {
      otpKeyInput().dispatchEvent(new Event("blur"));
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("OTP key is required");
      expect(fixture.nativeElement.textContent).not.toContain("exactly 32 characters");
    });

    it.each([
      ["shorter", "a".repeat(31)],
      ["longer", "a".repeat(33)]
    ])("renders only the length error for an OTP key %s than 32 characters", async (_, value) => {
      await typeInto(fixture, otpKeyInput(), value);
      otpKeyInput().dispatchEvent(new Event("blur"));
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("OTP key must be exactly 32 characters long.");
      expect(fixture.nativeElement.textContent).not.toContain("OTP key is required");
    });

    it("accepts an OTP key of exactly 32 characters", async () => {
      await typeInto(fixture, otpKeyInput(), "a".repeat(32));

      expect(component.otpKeyForm().valid()).toBe(true);
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
