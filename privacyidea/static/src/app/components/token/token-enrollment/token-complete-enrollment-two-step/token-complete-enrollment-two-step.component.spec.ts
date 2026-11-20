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

import { NO_ERRORS_SCHEMA } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ContentService } from "@services/content/content.service";
import { TokenService } from "@services/token/token.service";
import { axe } from "@testing/axe";
import { MockEnrollmentStepHost, mockEnrollmentStepHost } from "@testing/enrollment-step-host";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { MockTokenService } from "@testing/mock-services/mock-token-service";
import { of } from "rxjs";
import { TokenCompleteEnrollmentTwoStepComponent } from "./token-complete-enrollment-two-step.component";

describe("TokenCompleteEnrollmentTwoStepComponent", () => {
  let component: TokenCompleteEnrollmentTwoStepComponent;
  let fixture: ComponentFixture<TokenCompleteEnrollmentTwoStepComponent>;
  let mockTokenService: MockTokenService;
  let host: MockEnrollmentStepHost;

  const dialogData = {
    response: { detail: { serial: "123" }, type: "hotp" },
    enrollParameters: { data: { type: "hotp", twoStepInit: true } },
    onEnrollmentResponseChange: jest.fn()
  };

  const setup = async (data: unknown = dialogData) => {
    TestBed.resetTestingModule();
    host = mockEnrollmentStepHost(data);
    await TestBed.configureTestingModule({
      imports: [TokenCompleteEnrollmentTwoStepComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        host.provider
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenCompleteEnrollmentTwoStepComponent);
    component = fixture.componentInstance;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await setup();
  });

  it("registers itself as the step of the enrollment dialog", () => {
    expect(host.register).toHaveBeenCalledWith(component);
    expect(component.title()).toBe("Complete Token Enrollment");
    expect(component.headerState).toBe("incomplete");
  });

  it("should report a regenerated QR code to the opener of the dialog", () => {
    const regenerated = {
      type: "hotp",
      detail: { type: "hotp", serial: "123", googleurl: { img: "regenerated-img", value: "regenerated-url" } },
      result: { status: true }
    } as EnrollmentResponse;
    const enrollmentData = fixture.debugElement.query(By.css("app-token-enrollment-data"));
    enrollmentData.triggerEventHandler("enrollmentResponseChange", regenerated);

    expect(dialogData.onEnrollmentResponseChange).toHaveBeenCalledWith(regenerated);
  });

  it("shows the enrollment data for the type of the enrollment request", async () => {
    await setup({
      tokenType: "totp",
      // A /token/init response has no top-level type
      response: { result: { status: true }, detail: { serial: "TOTP0001", rollout_state: "clientwait" } },
      enrollParameters: { data: { type: "totp", twoStepInit: true } },
      onEnrollmentResponseChange: jest.fn()
    });

    const enrollmentData = fixture.debugElement.query(By.css("app-token-enrollment-data"));
    expect(enrollmentData.componentInstance.tokenType()).toBe("totp");
  });

  it("should disable enroll action if input is invalid", () => {
    component.clientPart.set("");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(true);
    expect(component.actions()[0].disabled).toBe(true);
  });

  it("should enable enroll action if input is valid", () => {
    component.clientPart.set("SOMEKEY");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(false);
    expect(component.actions()[0].disabled).toBe(false);
  });

  it("offers only Enroll; the dialog around it offers the way out", () => {
    expect(component.actions().map((action) => action.value)).toEqual(["enroll"]);
  });

  it("reports the completed enrollment to the flow", () => {
    const completed = {
      type: "hotp",
      detail: { type: "hotp", serial: "X", rollout_state: "enrolled" },
      result: { status: true }
    } as EnrollmentResponse;
    mockTokenService.enrollToken = jest.fn().mockReturnValue(of(completed));
    component.clientPart.set("SOMEKEY");
    component.onAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(host.flow.finishStep).toHaveBeenCalledWith(completed);
  });

  it("does not finish the step while the rollout state is client_wait", () => {
    mockTokenService.enrollToken = jest.fn().mockReturnValue(
      of({
        type: "hotp",
        detail: { type: "hotp", serial: "X", rollout_state: "client_wait" },
        result: { status: true }
      } as EnrollmentResponse)
    );
    component.clientPart.set("SOMEKEY");
    component.onAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(host.flow.finishStep).not.toHaveBeenCalled();
  });

  it("should remove twoStepInit from enrollParameters.data when enrolling", () => {
    component.clientPart.set("SOMEKEY");
    fixture.detectChanges();
    jest.spyOn(component["tokenService"], "enrollToken").mockImplementation((params) => {
      expect(params.data.type).toEqual("hotp");
      expect(params.data["twoStepInit"]).toBeUndefined();
      return of({
        result: { status: true },
        detail: { rollout_state: "enrolled", type: "hotp", serial: "123" },
        type: "hotp"
      });
    });
    component.onAction("enroll");
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
