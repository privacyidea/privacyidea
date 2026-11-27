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

import { HttpResourceRef, provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal, WritableSignal } from "@angular/core";
import { ValidationError } from "@angular/forms/signals";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { SmsEnrollmentData } from "@app/mappers/token-api-payload/sms-token-api-payload.mapper";
import { ContentService } from "@services/content/content.service";
import { SmsGateway, SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { SystemConfigResponse, SystemService } from "@services/system/system.service";
import { EnrollmentPolicies, EnrollmentPolicyState, TokenService } from "@services/token/token.service";
import { MockContentService, MockSmsGatewayService, MockSystemService, MockTokenService } from "@testing/mock-services";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { EnrollSmsComponent } from "./enroll-sms.component";
import { clearOverlays, clickCheckbox, flushFixture, matSelectAt, pickOption } from "@testing/enroll-form-dom";
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

type SystemConfigResourceValue = SystemConfigResponse | undefined;

describe("EnrollSmsComponent", () => {
  let component: EnrollSmsComponent;
  let fixture: ComponentFixture<EnrollSmsComponent>;
  let smsGatewayServiceMock: MockSmsGatewayService;
  let systemServiceMock: MockSystemService;

  const basicOptions: TokenEnrollmentData = { type: "sms" } as TokenEnrollmentData;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollSmsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: SmsGatewayService, useClass: MockSmsGatewayService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSmsComponent);
    component = fixture.componentInstance;
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
    it("should offer the gateways of the sms_gateways policy when available", () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1", "gw2", "gw3"] }));
      const opts = component.smsGatewayOptions();
      expect(opts).toEqual(["gw1", "gw2", "gw3"]);
    });

    it("should fall back to smsGateways service when no policy list applies", () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies());
      smsGatewayServiceMock.smsGateways.set([
        { name: "service-gw1", providermodule: "m", options: {}, headers: {} },
        { name: "service-gw2", providermodule: "m", options: {}, headers: {} }
      ]);
      const opts = component.smsGatewayOptions();
      expect(opts).toEqual(["service-gw1", "service-gw2"]);
    });

    it("should append the default identifier only when no policy list restricts the gateways", () => {
      (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
        MockPiResponse.fromValue({ "sms.identifier": "default-gw" })
      );
      expect(component.smsGatewayOptions()).toContain("default-gw");

      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1"] }));
      expect(component.smsGatewayOptions()).toEqual(["gw1"]);
    });
  });

  it("offers only the gateways of the enrollment policies", () => {
    (smsGatewayServiceMock as unknown as { smsGateways: WritableSignal<SmsGateway[]> }).smsGateways = signal<
      SmsGateway[]
    >([
      { name: "gw0", providermodule: "m", options: {}, headers: {} },
      { name: "gw1", providermodule: "m", options: {}, headers: {} },
      { name: "gw2", providermodule: "m", options: {}, headers: {} }
    ]);
    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1"] }));
    (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
      MockPiResponse.fromValue({ "sms.identifier": "gw0" })
    );
    fixture.detectChanges();
    TestBed.tick();

    expect(component.smsGatewayOptions()).toEqual(["gw1"]);
    expect(component.smsGateway()).not.toBe("gw0");
    expect(component.smsGatewayForm().disabled()).toBe(false);

    fixture.componentRef.setInput("enrollmentPolicies", { state: "pending" });
    fixture.detectChanges();
    TestBed.tick();

    expect(component.smsGatewayForm().disabled()).toBe(true);

    fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies());
    fixture.detectChanges();
    TestBed.tick();

    expect(component.smsGatewayOptions()).toEqual(["gw0", "gw1", "gw2"]);
    expect(component.smsGatewayForm().disabled()).toBe(false);
  });

  describe("gateway pick across policy reloads", () => {
    function loadWith(gateways: string[]) {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: gateways }));
      fixture.detectChanges();
      TestBed.tick();
    }

    beforeEach(() => {
      (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
        MockPiResponse.fromValue({ "sms.identifier": "gw0" })
      );
      loadWith(["gw0", "gw1", "gw2"]);
      component.smsGateway.set("gw2");
    });

    it("keeps the pick when the policies reload with the same gateways", () => {
      loadWith(["gw0", "gw1", "gw2"]);
      expect(component.smsGateway()).toBe("gw2");
    });

    it("keeps the pick when the policies reload with the gateways in another order", () => {
      loadWith(["gw2", "gw0", "gw1"]);
      expect(component.smsGateway()).toBe("gw2");
    });

    it("resets the pick to the default when the allowed gateways change", () => {
      loadWith(["gw0", "gw1"]);
      expect(component.smsGateway()).toBe("gw0");
    });
  });

  describe("gateway of the policies", () => {
    const gatewayField = () => fixture.nativeElement.querySelector("mat-select");
    const applyPolicies = (gateways: string[]) => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: gateways }));
      fixture.detectChanges();
      TestBed.tick();
      fixture.detectChanges();
    };

    beforeEach(() => {
      (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
        MockPiResponse.fromValue({ "sms.identifier": "gw0" })
      );
      component.phoneNumber.set("+12345678");
    });

    it("hides the gateway field and sends no gateway without an sms_gateways policy", () => {
      applyPolicies([]);

      expect(gatewayField()).toBeNull();
      const args = component.buildEnrollmentArgs(basicOptions);
      expect(args).not.toBeNull();
      expect(Object.keys(args!.mapper.toApiPayload(args!.data))).not.toContain("sms.identifier");
    });

    it("sends no gateway of the enrollment data without an sms_gateways policy", () => {
      fixture.componentRef.setInput("enrollmentData", { type: "sms", smsGateway: "gw1" } as SmsEnrollmentData);
      applyPolicies([]);

      const args = component.buildEnrollmentArgs(basicOptions);
      expect(Object.keys(args!.mapper.toApiPayload(args!.data))).not.toContain("sms.identifier");
    });

    it("shows the gateway field and sends the gateway with an sms_gateways policy", () => {
      applyPolicies(["gw0", "gw1"]);

      expect(gatewayField()).not.toBeNull();
      const args = component.buildEnrollmentArgs(basicOptions);
      expect(args!.mapper.toApiPayload(args!.data)["sms.identifier"]).toBe("gw0");
    });

    it("keeps the gateway field, disabled, while the policies load", () => {
      fixture.componentRef.setInput("enrollmentPolicies", { state: "pending" });
      fixture.detectChanges();

      expect(gatewayField()).not.toBeNull();
      expect(component.smsGatewayForm().disabled()).toBe(true);
    });
  });

  describe("container template editor without a policy target", () => {
    const gatewayField = () => fixture.nativeElement.querySelector("mat-select");

    beforeEach(() => {
      (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
        MockPiResponse.fromValue({ "sms.identifier": "gw0" })
      );
      smsGatewayServiceMock.smsGateways.set([
        { name: "gw1", providermodule: "m", options: {}, headers: {} },
        { name: "gw2", providermodule: "m", options: {}, headers: {} }
      ]);
      fixture.componentRef.setInput("enrollmentPolicies", { state: "unrestricted" });
      component.phoneNumber.set("+12345678");
    });

    it("offers the gateway field with all gateways and the system gateway choice", async () => {
      await flushFixture(fixture);

      expect(gatewayField()).not.toBeNull();
      await pickOption(fixture, matSelectAt(fixture), 2);

      expect(component.smsGateway()).toBe("gw2");
      const args = component.buildEnrollmentArgs(basicOptions);
      expect(args!.mapper.toApiPayload(args!.data)["sms.identifier"]).toBe("gw2");
    });

    it("keeps the gateway of a stored template on save", () => {
      fixture.componentRef.setInput("enrollmentData", { type: "sms", smsGateway: "gw1" } as SmsEnrollmentData);
      fixture.detectChanges();

      const args = component.buildEnrollmentArgs(basicOptions);
      expect(args!.mapper.toApiPayload(args!.data)["sms.identifier"]).toBe("gw1");
    });

    it("sends no gateway for the system gateway choice", () => {
      component.smsGateway.set("");

      const args = component.buildEnrollmentArgs(basicOptions);
      expect(args).not.toBeNull();
      expect(args!.mapper.toApiPayload(args!.data)).not.toHaveProperty("sms.identifier");
    });
  });

  describe("defaultSMSGatewayIsSet", () => {
    it("should be false when no sms gateway is configured", () => {
      (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
        MockPiResponse.fromValue({})
      );
      expect(component.defaultSMSGatewayIsSet()).toBe(false);
    });

    it("should be true when sms.identifier is configured", () => {
      (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
        MockPiResponse.fromValue({ "sms.identifier": "main-gw" })
      );
      expect(component.defaultSMSGatewayIsSet()).toBe(true);
    });
  });

  describe("optional gateway with a system default", () => {
    const setDefault = (id?: string) =>
      (systemServiceMock.systemConfigResource as HttpResourceRef<SystemConfigResourceValue>).value.set(
        id ? MockPiResponse.fromValue({ "sms.identifier": id }) : MockPiResponse.fromValue({})
      );
    const settle = () => {
      fixture.detectChanges();
      TestBed.tick();
    };

    it("leaves the gateway empty and valid when the default is not on the policy list, and sends no identifier", () => {
      setDefault("gw0");
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1"] }));
      settle();
      component.phoneNumber.set("+12345678");

      expect(component.smsGateway()).toBe("");
      expect(component.smsGatewayForm().valid()).toBe(true);
      const args = component.buildEnrollmentArgs(basicOptions);
      expect(args).not.toBeNull();
      expect(args!.mapper.toApiPayload(args!.data)).not.toHaveProperty("sms.identifier");
    });

    it("keeps the gateway required without a system default", () => {
      setDefault();
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1"] }));
      settle();
      component.phoneNumber.set("+12345678");

      expect(component.smsGatewayForm().valid()).toBe(false);
      expect(component.buildEnrollmentArgs(basicOptions)).toBeNull();
    });

    it("preselects and sends the default when it is on the policy list", () => {
      setDefault("gw1");
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1", "gw2"] }));
      settle();
      component.phoneNumber.set("+12345678");

      expect(component.smsGateway()).toBe("gw1");
      const args = component.buildEnrollmentArgs(basicOptions);
      expect(args!.mapper.toApiPayload(args!.data)).toEqual(expect.objectContaining({ "sms.identifier": "gw1" }));
    });
  });

  describe("buildEnrollmentArgs", () => {
    it("should return null and mark smsGateway form touched when no gateway selected", () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1", "gw-b"] }));
      TestBed.tick();
      component.smsGateway.set("");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.smsGatewayForm().touched()).toBe(true);
    });

    it("should return null and mark phoneNumber form touched when phone number is invalid", () => {
      component.smsGateway.set("gw1");
      component.readNumberDynamically.set(false);
      component.phoneNumber.set("not-a-number");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.phoneNumberForm().touched()).toBe(true);
    });

    it("should skip phoneNumber validation when readNumberDynamically is true", () => {
      component.smsGateway.set("gw1");
      component.readNumberDynamically.set(true);
      component.phoneNumber.set("");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.readNumberDynamically).toBe(true);
      expect((result!.data as SmsEnrollmentData).phoneNumber).toBeUndefined();
    });

    it("should include phoneNumber when readNumberDynamically is false", () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw1", "gw-b"] }));
      TestBed.tick();
      component.smsGateway.set("gw1");
      component.readNumberDynamically.set(false);
      component.phoneNumber.set("+12345678");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.smsGateway).toBe("gw1");
      expect((result!.data as SmsEnrollmentData).phoneNumber).toBe("+12345678");
    });
  });

  describe("phoneNumberForm validation", () => {
    it("should reject malformed numbers", () => {
      component.phoneNumber.set("abc");
      expect(
        component
          .phoneNumberForm()
          .errors()
          .some((e: ValidationError) => e.kind === "invalidPhoneNumber")
      ).toBe(true);
    });

    it("should accept E.164-style numbers", () => {
      component.phoneNumber.set("+4915112345678");
      expect(
        component
          .phoneNumberForm()
          .errors()
          .some((e: ValidationError) => e.kind === "invalidPhoneNumber")
      ).toBe(false);
    });
  });

  describe("onSmsConfigKeydown", () => {
    it("should navigate when Enter pressed", () => {
      const spy = jest.spyOn(component, "goToSmsConfig").mockReturnValue();
      component.onSmsConfigKeydown(new KeyboardEvent("keydown", { key: "Enter" }));
      expect(spy).toHaveBeenCalled();
    });

    it("should navigate when Space pressed", () => {
      const spy = jest.spyOn(component, "goToSmsConfig").mockReturnValue();
      component.onSmsConfigKeydown(new KeyboardEvent("keydown", { key: " " }));
      expect(spy).toHaveBeenCalled();
    });

    it("should ignore other keys", () => {
      const spy = jest.spyOn(component, "goToSmsConfig").mockReturnValue();
      component.onSmsConfigKeydown(new KeyboardEvent("keydown", { key: "a" }));
      expect(spy).not.toHaveBeenCalled();
    });
  });

  describe("bound controls", () => {
    afterEach(clearOverlays);

    it("writes a click on the checkbox to the model, marks it dirty and disables the phone number", async () => {
      expect(component.phoneNumberForm().disabled()).toBe(false);

      await clickCheckbox(fixture);

      expect(component.readNumberDynamically()).toBe(true);
      expect(component.readNumberDynamicallyForm().dirty()).toBe(true);
      expect(component.phoneNumberForm().disabled()).toBe(true);
    });

    it("writes the picked SMS gateway to the model", async () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw-a", "gw-b"] }));
      await flushFixture(fixture);

      await pickOption(fixture, matSelectAt(fixture), 1);

      expect(component.smsGateway()).toBe("gw-b");
      expect(component.smsGatewayForm().dirty()).toBe(true);
    });

    it("renders the required error of the gateway select once the build was refused", async () => {
      fixture.componentRef.setInput("enrollmentPolicies", loadedPolicies({ sms_gateways: ["gw-a", "gw-b"] }));
      TestBed.tick();
      expect(component.buildEnrollmentArgs(basicOptions)).toBeNull();
      await flushFixture(fixture);

      expect(fixture.nativeElement.textContent).toContain("SMS Gateway is required");
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
