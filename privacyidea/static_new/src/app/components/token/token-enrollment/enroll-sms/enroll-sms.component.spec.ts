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
import { signal } from "@angular/core";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { AuthService } from "@services/auth/auth.service";
import { SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { SystemService } from "@services/system/system.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockSmsGatewayService } from "@testing/mock-services/mock-sms-gateway-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { EnrollSmsComponent } from "./enroll-sms.component";

describe("EnrollSmsComponent", () => {
  let component: EnrollSmsComponent;
  let fixture: ComponentFixture<EnrollSmsComponent>;
  let authServiceMock: MockAuthService;
  let smsGatewayServiceMock: MockSmsGatewayService;
  let systemServiceMock: MockSystemService;

  const basicOptions: TokenEnrollmentData = { type: "sms" } as any;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollSmsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: SmsGatewayService, useClass: MockSmsGatewayService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSmsComponent);
    component = fixture.componentInstance;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    smsGatewayServiceMock = TestBed.inject(SmsGatewayService) as unknown as MockSmsGatewayService;
    systemServiceMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "sms",
        smsGateway: "TestGateway",
        readNumberDynamically: true,
        phoneNumber: "+1234567890"
      });
      fixture.detectChanges();
      component.ngOnInit();
      expect(component.smsGateway()).toBe("TestGateway");
      expect(component.readNumberDynamically()).toBe(true);
      expect(component.phoneNumber()).toBe("+1234567890");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "sms",
        smsGateway: undefined,
        readNumberDynamically: undefined,
        phoneNumber: undefined
      });
      component.ngOnInit();
      expect(component.smsGateway()).toBe("");
      expect(component.readNumberDynamically()).toBe(false);
      expect(component.phoneNumber()).toBe("");
    });
  });

  describe("smsGatewayOptions computed", () => {
    it("should parse gateways from the sms_gateways right when available", () => {
      authServiceMock.authData.set({ rights: ["sms_gateways=gw1 gw2 gw3"] } as any);
      const opts = component.smsGatewayOptions();
      expect(opts).toEqual(["gw1", "gw2", "gw3"]);
    });

    it("should fall back to smsGateways service when no right exists", () => {
      authServiceMock.authData.set({ rights: [] } as any);
      (smsGatewayServiceMock as any).smsGateways = signal([
        { name: "service-gw1", providermodule: "m", options: {}, headers: {} },
        { name: "service-gw2", providermodule: "m", options: {}, headers: {} }
      ]);
      const opts = component.smsGatewayOptions();
      expect(opts).toEqual(["service-gw1", "service-gw2"]);
    });

    it("should append the default identifier when not already present", () => {
      authServiceMock.authData.set({ rights: ["sms_gateways=gw1"] } as any);
      (systemServiceMock.systemConfigResource as any).value.set({
        result: { value: { "sms.identifier": "default-gw" } }
      });
      const opts = component.smsGatewayOptions();
      expect(opts).toContain("default-gw");
      expect(opts).toContain("gw1");
    });
  });

  describe("defaultSMSGatewayIsSet", () => {
    it("should be false when no sms gateway is configured", () => {
      (systemServiceMock.systemConfigResource as any).value.set({
        result: { value: {} }
      });
      expect(component.defaultSMSGatewayIsSet()).toBe(false);
    });

    it("should be true when sms.identifier is configured", () => {
      (systemServiceMock.systemConfigResource as any).value.set({
        result: { value: { "sms.identifier": "main-gw" } }
      });
      expect(component.defaultSMSGatewayIsSet()).toBe(true);
    });
  });

  describe("enrollmentArgsGetter", () => {
    it("should return null and mark smsGateway form touched when no gateway selected", () => {
      component.smsGateway.set("");
      const result = component.enrollmentArgsGetter(basicOptions);
      expect(result).toBeNull();
      expect(component.smsGatewayForm().touched()).toBe(true);
    });

    it("should return null and mark phoneNumber form touched when phone number is invalid", () => {
      component.smsGateway.set("gw1");
      component.readNumberDynamically.set(false);
      component.phoneNumber.set("not-a-number");
      const result = component.enrollmentArgsGetter(basicOptions);
      expect(result).toBeNull();
      expect(component.phoneNumberForm().touched()).toBe(true);
    });

    it("should skip phoneNumber validation when readNumberDynamically is true", () => {
      component.smsGateway.set("gw1");
      component.readNumberDynamically.set(true);
      component.phoneNumber.set("");
      const result = component.enrollmentArgsGetter(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.readNumberDynamically).toBe(true);
      expect((result!.data as any).phoneNumber).toBeUndefined();
    });

    it("should include phoneNumber when readNumberDynamically is false", () => {
      component.smsGateway.set("gw1");
      component.readNumberDynamically.set(false);
      component.phoneNumber.set("+12345678");
      const result = component.enrollmentArgsGetter(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.smsGateway).toBe("gw1");
      expect((result!.data as any).phoneNumber).toBe("+12345678");
    });
  });

  describe("phoneNumberForm validation", () => {
    it("should reject malformed numbers", () => {
      component.phoneNumber.set("abc");
      expect(
        component.phoneNumberForm().errors().some((e: any) => e.kind === "invalidPhoneNumber")
      ).toBe(true);
    });

    it("should accept E.164-style numbers", () => {
      component.phoneNumber.set("+4915112345678");
      expect(
        component.phoneNumberForm().errors().some((e: any) => e.kind === "invalidPhoneNumber")
      ).toBe(false);
    });
  });

  describe("onSmsConfigKeydown", () => {
    it("should navigate when Enter pressed", () => {
      const spy = jest.spyOn(component, "goToSmsConfig").mockImplementation(() => {});
      component.onSmsConfigKeydown(new KeyboardEvent("keydown", { key: "Enter" }));
      expect(spy).toHaveBeenCalled();
    });

    it("should navigate when Space pressed", () => {
      const spy = jest.spyOn(component, "goToSmsConfig").mockImplementation(() => {});
      component.onSmsConfigKeydown(new KeyboardEvent("keydown", { key: " " }));
      expect(spy).toHaveBeenCalled();
    });

    it("should ignore other keys", () => {
      const spy = jest.spyOn(component, "goToSmsConfig").mockImplementation(() => {});
      component.onSmsConfigKeydown(new KeyboardEvent("keydown", { key: "a" }));
      expect(spy).not.toHaveBeenCalled();
    });
  });
});
