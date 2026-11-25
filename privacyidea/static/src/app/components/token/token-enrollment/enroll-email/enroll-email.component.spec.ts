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
import { EnrollEmailComponent } from "./enroll-email.component";
import { SystemService } from "@services/system/system.service";
import { MockSystemService, MockTokenService } from "@testing/mock-services";
import { TokenService } from "@services/token/token.service";
import { clickCheckbox, flushFixture, typeInto } from "@testing/enroll-form-dom";
import { axe } from "@testing/axe";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";

describe("EnrollEmailComponent", () => {
  let component: EnrollEmailComponent;
  let fixture: ComponentFixture<EnrollEmailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollEmailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: SystemService, useClass: MockSystemService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollEmailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "email",
        emailAddress: "test@example.com",
        readEmailDynamically: true
      });
      component.ngOnInit();
      expect(component.emailAddress()).toBe("test@example.com");
      expect(component.readEmailDynamically()).toBe(true);
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "email",
        emailAddress: undefined,
        readEmailDynamically: undefined
      });
      component.ngOnInit();
      expect(component.emailAddress()).toBe("");
      expect(component.readEmailDynamically()).toBe(false);
    });
  });

  it("writes a click on the checkbox to the model, marks it dirty and disables the address field", async () => {
    expect(fixture.nativeElement.querySelector("input[matInput]").disabled).toBe(false);

    await clickCheckbox(fixture);

    expect(component.readEmailDynamically()).toBe(true);
    expect(component.readEmailDynamicallyForm().dirty()).toBe(true);
    expect(fixture.nativeElement.querySelector("input[matInput]").disabled).toBe(true);
  });

  it("renders only the required error for an empty address on enrollment", async () => {
    expect(component.buildEnrollmentArgs({ type: "email" } as TokenEnrollmentData)).toBeNull();
    await flushFixture(fixture);

    expect(fixture.nativeElement.textContent).toContain("Email Address is required");
    expect(fixture.nativeElement.textContent).not.toContain("name@example.com");
  });

  it("renders only the format error for a malformed address on enrollment", async () => {
    await typeInto(fixture, fixture.nativeElement.querySelector("input[matInput]"), "name@example");
    expect(component.buildEnrollmentArgs({ type: "email" } as TokenEnrollmentData)).toBeNull();
    await flushFixture(fixture);

    expect(fixture.nativeElement.textContent).toContain("Enter an email address like name@example.com.");
    expect(fixture.nativeElement.textContent).not.toContain("Email Address is required");
  });

  it("accepts an address with a dot in the domain", async () => {
    await typeInto(fixture, fixture.nativeElement.querySelector("input[matInput]"), "name@example.com");

    expect(component.buildEnrollmentArgs({ type: "email" } as TokenEnrollmentData)).not.toBeNull();
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
