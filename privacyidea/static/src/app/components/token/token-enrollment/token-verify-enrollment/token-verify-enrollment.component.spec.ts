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
import { TokenVerifyEnrollmentComponent } from "./token-verify-enrollment.component";

describe("TokenVerifyEnrollmentComponent", () => {
  let component: TokenVerifyEnrollmentComponent;
  let fixture: ComponentFixture<TokenVerifyEnrollmentComponent>;
  let mockTokenService: MockTokenService;
  let host: MockEnrollmentStepHost;

  const dialogData = {
    response: { detail: { serial: "123", verify: { message: "Enter OTP" } }, type: "hotp" },
    enrollParameters: { data: {} },
    onEnrollmentResponseChange: jest.fn()
  };

  const setup = async (data: unknown = dialogData) => {
    TestBed.resetTestingModule();
    host = mockEnrollmentStepHost(data);
    await TestBed.configureTestingModule({
      imports: [TokenVerifyEnrollmentComponent],
      providers: [
        provideHttpClient(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        host.provider
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenVerifyEnrollmentComponent);
    component = fixture.componentInstance;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await setup();
  });

  it("registers itself as the step of the enrollment dialog", () => {
    expect(host.register).toHaveBeenCalledWith(component);
    expect(component.title()).toBe("Verify Token Enrollment");
    expect(component.headerState).toBe("verify");
  });

  it("shows the enrollment data for the enrolled token type", async () => {
    await setup({
      tokenType: "hotp",
      response: {
        result: { status: true },
        detail: {
          serial: "PIEM0001",
          rollout_state: "verify",
          verify: { message: "Enter OTP" },
          googleurl: { description: "", img: "data:image/png;base64,QR", value: "otpauth://hotp/PIEM0001" },
          otpkey: { description: "", img: "", value: "seed://3132", value_b32: "GEZA" }
        }
      },
      enrollParameters: { data: { type: "email" } },
      onEnrollmentResponseChange: jest.fn()
    });

    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector("img.enrollment-data__qr")).toBeNull();
    expect(element.querySelector("app-otp-key")).toBeNull();
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

  it("should render the verification message outside the input so it is not capped to its width", () => {
    const message = fixture.debugElement
      .queryAll(By.css("div"))
      .find((element) => element.nativeElement.textContent.trim() === "Enter OTP");

    expect(message).toBeTruthy();
    expect(fixture.debugElement.query(By.css("mat-hint"))).toBeNull();
    expect(message!.nativeElement.closest("mat-form-field")).toBeNull();
  });

  it("should disable verify action if input is invalid", () => {
    component.verifyOTP_value.set("");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(true);
    expect(component.actions()[0].disabled).toBe(true);
  });

  it("should enable verify action if input is valid", () => {
    component.verifyOTP_value.set("123456");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(false);
    expect(component.actions()[0].disabled).toBe(false);
  });

  it("offers only Verify; the dialog around it offers the way out", () => {
    expect(component.actions().map((action) => action.value)).toEqual(["verify"]);
  });

  it("reports the verified token to the flow", () => {
    component.verifyOTP_value.set("123456");
    component.onAction("verify");
    expect(mockTokenService.verifyToken).toHaveBeenCalledWith("123", "123456");
    expect(host.flow.finishStep).toHaveBeenCalled();
  });

  it("does not send a verify request without the serial of the enrolled token", () => {
    (component as unknown as { responseDetails: undefined }).responseDetails = undefined;
    mockTokenService.verifyToken.mockClear();
    component.verifyOTP_value.set("123456");
    component.onAction("verify");
    expect(mockTokenService.verifyToken).not.toHaveBeenCalled();
    expect(host.flow.finishStep).not.toHaveBeenCalled();
  });

  it("does not finish the step if the rollout state is not enrolled", () => {
    mockTokenService.verifyToken = jest.fn().mockReturnValue(
      of({
        result: { status: true },
        detail: { rollout_state: "client_wait", serial: "123", type: "hotp" },
        type: "hotp"
      })
    );
    component.verifyOTP_value.set("123456");
    component.onAction("verify");
    expect(mockTokenService.verifyToken).toHaveBeenCalled();
    expect(host.flow.finishStep).not.toHaveBeenCalled();
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
