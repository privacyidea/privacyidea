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
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollMotpComponent } from "./enroll-motp.component";
import { TokenService } from "@services/token/token.service";
import { MockTokenService } from "@testing/mock-services";

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
  } as any;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollMotpComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService }]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollMotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initially have generateOnServer true and otpKey form disabled", () => {
    expect(component.generateOnServer()).toBe(true);
    expect(component.otpKey()).toEqual("");
    expect(component.otpKeyForm().disabled()).toBe(true);
  });

  describe("motpPinForm validation", () => {
    it("should require motpPin", () => {
      expect(component.motpPinForm().errors().some((e: any) => e.kind === "required")).toBe(true);
    });

    it("should reject pin shorter than 4 chars", () => {
      component.motpPin.set("abc");
      expect(component.motpPinForm().errors().some((e: any) => e.kind === "minlength")).toBe(true);
    });

    it("should accept pin of 4 chars or longer", () => {
      component.motpPin.set("abcd");
      expect(component.motpPinForm().errors().some((e: any) => e.kind === "minlength")).toBe(false);
    });
  });

  describe("repeatMotpPinForm validation", () => {
    it("should fail when repeat differs from motpPin", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abce");
      expect(component.repeatMotpPinForm().errors().some((e: any) => e.kind === "motpPinMismatch")).toBe(true);
    });

    it("should pass when repeat matches motpPin", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abcd");
      expect(component.repeatMotpPinForm().errors().some((e: any) => e.kind === "motpPinMismatch")).toBe(false);
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
      expect((result!.data as any).otpKey).toBeUndefined();
    });

    it("should include otpKey when generateOnServer is false", () => {
      component.motpPin.set("abcd");
      component.repeatMotpPin.set("abcd");
      component.generateOnServer.set(false);
      component.otpKey.set("ABCDEF");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect((result!.data as any).otpKey).toBe("ABCDEF");
      expect(result!.data.generateOnServer).toBe(false);
    });
  });
});
