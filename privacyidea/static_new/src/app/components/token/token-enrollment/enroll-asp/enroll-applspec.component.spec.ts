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
import { EnrollApplspecComponent } from "./enroll-applspec.component";
import { ServiceIdService } from "@services/service-id/service-id.service";
import { MockServiceIdService, MockTokenService } from "@testing/mock-services";
import { TokenService } from "@services/token/token.service";

describe("EnrollAspComponent", () => {
  let component: EnrollApplspecComponent;
  let fixture: ComponentFixture<EnrollApplspecComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollApplspecComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ServiceIdService, useClass: MockServiceIdService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollApplspecComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
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
