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
import { TokenService } from "@services/token/token.service";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";

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
});
