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
import { Subject } from "rxjs";
import { TokenCompleteEnrollmentTwoStepComponent } from "./token-complete-enrollment-two-step.component";

describe("TokenCompleteEnrollmentTwoStepComponent", () => {
  let component: TokenCompleteEnrollmentTwoStepComponent;
  let fixture: ComponentFixture<TokenCompleteEnrollmentTwoStepComponent>;
  let mockTokenService: MockTokenService;
  let host: MockEnrollmentStepHost;

  const dialogData = {
    response: { detail: { serial: "123", "2step_output": 20 }, type: "hotp" },
    enrollParameters: { data: { type: "hotp", twoStepInit: true } },
    onEnrollmentResponseChange: jest.fn()
  };

  const setup = async (data: unknown = dialogData, state: { sentInput?: string } = {}) => {
    TestBed.resetTestingModule();
    host = mockEnrollmentStepHost(data, state);
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

  describe("on Enroll", () => {
    const completed = {
      type: "hotp",
      detail: { type: "hotp", serial: "123", rollout_state: "enrolled" },
      result: { status: true }
    } as EnrollmentResponse;
    let request: Subject<EnrollmentResponse>;
    let toResult: (response: EnrollmentResponse) => EnrollmentResponse | null;

    beforeEach(() => {
      request = new Subject<EnrollmentResponse>();
      mockTokenService.enrollToken = jest.fn().mockReturnValue(request);
      component.clientPart.set("SOMEKEY");
      component.onAction("enroll");
      toResult = host.flow.sendStepRequest.mock.calls[0][1];
    });

    it("lets the flow send the client part, without twoStepInit", () => {
      expect(mockTokenService.enrollToken).toHaveBeenCalledWith({
        data: {
          type: "hotp",
          serial: "123",
          otpKey: "SOMEKEY",
          otpKeyFormat: "base32check",
          generateOnServer: false
        }
      });
      expect(host.flow.sendStepRequest).toHaveBeenCalledWith(request, expect.any(Function), "SOMEKEY");
    });

    it("leaves the enrollment parameters unchanged for Regenerate QR Code", () => {
      expect(dialogData.enrollParameters.data).toEqual({ type: "hotp", twoStepInit: true });
    });

    it("finishes the step with the completed enrollment", () => {
      expect(toResult(completed)).toBe(completed);
    });

    it("does not finish the step while the rollout state is clientwait", () => {
      const waiting = { ...completed, detail: { ...completed.detail, rollout_state: "clientwait" } };

      expect(toResult(waiting as EnrollmentResponse)).toBeNull();
    });
  });

  describe("while the flow sends the client part", () => {
    beforeEach(() => {
      host.flow.sentInput.set("SOMEKEY");
      fixture.detectChanges();
    });

    it("disables Enroll and does not send it again", () => {
      component.onAction("enroll");

      expect(component.actions()[0].disabled).toBe(true);
      expect(host.flow.sendStepRequest).not.toHaveBeenCalled();
    });

    it("enables Enroll and the input again once the request ended", () => {
      component.clientPart.set("SOMEKEY");
      host.flow.sentInput.set(null);
      fixture.detectChanges();

      expect(component.actions()[0].disabled).toBe(false);
      expect(fixture.nativeElement.querySelector("input").readOnly).toBe(false);
    });
  });

  it("shows the sent client part read-only when it is reopened while the request runs", async () => {
    await setup(dialogData, { sentInput: "SOMEKEY" });
    await fixture.whenStable();

    const input: HTMLInputElement = fixture.nativeElement.querySelector("input");
    expect(input.value).toBe("SOMEKEY");
    expect(input.readOnly).toBe(true);
    expect(component.actions()[0].disabled).toBe(true);
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
