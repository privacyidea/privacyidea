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
import { MatSelect } from "@angular/material/select";
import { MatTooltip } from "@angular/material/tooltip";
import { By } from "@angular/platform-browser";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollApplspecComponent } from "./enroll-applspec.component";
import { ServiceIdService } from "@services/service-id/service-id.service";
import { MockServiceIdService, MockTokenService } from "@testing/mock-services";
import { EnrollmentPolicies, EnrollmentPolicyState, TokenService } from "@services/token/token.service";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { clickCheckbox } from "@testing/enroll-form-dom";
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

describe("EnrollAspComponent", () => {
  let component: EnrollApplspecComponent;
  let fixture: ComponentFixture<EnrollApplspecComponent>;
  let serviceIdService: MockServiceIdService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollApplspecComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ServiceIdService, useClass: MockServiceIdService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    serviceIdService = TestBed.inject(ServiceIdService) as unknown as MockServiceIdService;
    fixture = TestBed.createComponent(EnrollApplspecComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should offer the configured service IDs in a select when they can be listed", () => {
    serviceIdService.serviceIds.set([
      { servicename: "mail", description: "" },
      { servicename: "vpn", description: "" }
    ]);
    fixture.detectChanges();

    const select: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
    expect(select.options.map((option) => option.value)).toEqual(["mail", "vpn"]);
  });

  it("should show the required error for an empty service ID on enrollment", () => {
    expect(component.buildEnrollmentArgs({ type: "applspec" } as TokenEnrollmentData)).toBeNull();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Service ID is required");
  });

  it("should not block the enrollment when the service IDs can be listed", () => {
    expect(component.enrollmentBlockedReason()).toBeNull();
    const select: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
    expect(select.disabled).toBe(false);
  });

  describe("when the service IDs cannot be listed", () => {
    beforeEach(() => {
      serviceIdService.canListServiceIds.set(false);
      serviceIdService.serviceIdsUnavailableReason.set("needs serviceid_list");
      fixture.detectChanges();
    });

    it("should disable the service ID select and give the reason in its tooltip", () => {
      const select: MatSelect = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
      expect(select.disabled).toBe(true);

      const tooltip: MatTooltip = fixture.debugElement.query(By.directive(MatTooltip)).injector.get(MatTooltip);
      expect(tooltip.disabled).toBe(false);
      expect(tooltip.message).toBe("needs serviceid_list");
    });

    it("should report the enrollment as blocked and build no enrollment data", () => {
      expect(component.enrollmentBlockedReason()).toBe("needs serviceid_list");
      expect(component.buildEnrollmentArgs({ type: "applspec" } as TokenEnrollmentData)).toBeNull();
    });

    it("should not block the enrollment when enrollmentData already names the service ID", () => {
      fixture.componentRef.setInput("enrollmentData", { type: "applspec", serviceId: "mail" });
      component.ngOnInit();

      expect(component.enrollmentBlockedReason()).toBeNull();
    });
  });

  it("should initialize signals with default values", () => {
    expect(component.serviceId()).toBe("");
    expect(component.generateOnServer()).toBe(true);
    expect(component.otpKey()).toBe("");
  });

  it("locks generate on server when forced", () => {
    const generateOnServerCheckbox = () =>
      fixture.nativeElement.querySelector("mat-checkbox input[type='checkbox']") as HTMLInputElement;
    const keyInput = () => fixture.nativeElement.querySelector("input[placeholder='Enter static password']");
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

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "applspec",
        serviceId: "service-123",
        generateOnServer: false
      });
      component.ngOnInit();
      expect(component.serviceId()).toBe("service-123");
      expect(component.generateOnServer()).toBe(false);
      expect(component.otpKey()).toBe("");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "applspec",
        serviceId: undefined,
        generateOnServer: undefined,
        otpKey: undefined
      });
      component.ngOnInit();
      expect(component.serviceId()).toBe("");
      expect(component.generateOnServer()).toBe(true);
      expect(component.otpKey()).toBe("");
    });
  });

  describe("key input visibility", () => {
    const keyInput = () => fixture.nativeElement.querySelector("input[placeholder='Enter static password']");
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

  it("writes a click on the checkbox to the model and enables the password field", async () => {
    await clickCheckbox(fixture);

    expect(component.generateOnServer()).toBe(false);
    expect(component.generateOnServerForm().dirty()).toBe(true);
    expect(component.otpKeyForm().disabled()).toBe(false);
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
