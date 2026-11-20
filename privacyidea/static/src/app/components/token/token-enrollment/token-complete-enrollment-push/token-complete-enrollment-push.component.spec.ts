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
import { TestBed } from "@angular/core/testing";
import { PiResponse } from "@app/app.component";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { NotificationService } from "@services/notification/notification.service";
import { TokenDetails, Tokens, TokenService } from "@services/token/token.service";
import { axe } from "@testing/axe";
import { MockEnrollmentStepHost, mockEnrollmentStepHost } from "@testing/enrollment-step-host";
import { MockNotificationService, MockTokenService } from "@testing/mock-services";
import { NEVER, Observable, of, Subject, throwError } from "rxjs";
import { TokenCompleteEnrollmentPushComponent } from "./token-complete-enrollment-push.component";

const initResponse = (detail: Record<string, unknown> = {}) =>
  ({
    result: { status: true, value: true },
    type: "push",
    detail: {
      serial: "PIPU0001",
      rollout_state: "clientwait",
      pushurl: { description: "", img: "data:image/png;base64,QR", value: "otpauth://pipush/PIPU0001" },
      ...detail
    }
  }) as unknown as EnrollmentResponse;

const pollResponse = (tokens: Partial<TokenDetails>[] | undefined) =>
  ({
    result: { status: true, value: tokens ? { tokens, count: tokens.length, current: 1 } : undefined }
  }) as PiResponse<Tokens>;

describe("TokenCompleteEnrollmentPushComponent", () => {
  let host: MockEnrollmentStepHost;
  let tokenService: MockTokenService;
  let notificationService: MockNotificationService;

  const setup = (
    poll: Observable<PiResponse<Tokens>> = NEVER,
    options: { response?: EnrollmentResponse; reopened?: boolean } = {}
  ) => {
    TestBed.resetTestingModule();
    host = mockEnrollmentStepHost({ tokenType: "push", response: options.response ?? initResponse() }, options);
    TestBed.configureTestingModule({
      imports: [TokenCompleteEnrollmentPushComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService },
        host.provider
      ]
    });
    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    tokenService.pollTokenRolloutState.mockReturnValue(poll);
    const fixture = TestBed.createComponent(TokenCompleteEnrollmentPushComponent);
    fixture.detectChanges();
    return fixture;
  };

  it("registers as an incomplete step that warns about scanned QR codes before deleting", () => {
    const fixture = setup();
    const step = fixture.componentInstance;

    expect(host.register).toHaveBeenCalledWith(step);
    expect(step.title()).toBe("Take Action on Your Authenticator");
    expect(step.headerState).toBe("incomplete");
    expect(step.actions()).toEqual([]);
    expect(step.deleteWarning).toContain("QR code");
  });

  it("shows the QR code and the link for the smartphone", () => {
    const element: HTMLElement = setup().nativeElement;

    expect(element.querySelector("img")?.getAttribute("src")).toBe("data:image/png;base64,QR");
    expect(element.textContent).toContain("Please scan the QR code with the privacyIDEA Authenticator App");
    expect(element.querySelector("a")).toBeTruthy();
  });

  it("gives the user time to scan before the first poll, but checks at once after a reopen", () => {
    setup();
    expect(tokenService.pollTokenRolloutState).toHaveBeenCalledWith({ tokenSerial: "PIPU0001", initDelay: 5000 });

    setup(NEVER, { reopened: true });
    expect(tokenService.pollTokenRolloutState).toHaveBeenCalledWith({ tokenSerial: "PIPU0001", initDelay: 0 });
  });

  it("waits while the token is in clientwait", () => {
    setup(of(pollResponse([{ rollout_state: "clientwait" }])));

    expect(host.flow.finishStep).not.toHaveBeenCalled();
  });

  it("finishes the step with the rollout state the app reached", () => {
    setup(of(pollResponse([{ rollout_state: "enrolled" }])));

    expect(host.flow.finishStep).toHaveBeenCalledWith(initResponse({ rollout_state: "enrolled" }));
  });

  it("falls back to the rollout state of the first response when the poll carries no token", () => {
    const response = initResponse({ rollout_state: "enrolled" });
    setup(of(pollResponse(undefined)), { response });

    expect(host.flow.finishStep).toHaveBeenCalledWith(response);
  });

  it("ends the enrollment with a warning once the token no longer exists", () => {
    setup(of(pollResponse([])));

    expect(notificationService.warning).toHaveBeenCalledWith(
      "The token PIPU0001 no longer exists. The enrollment was ended."
    );
    expect(host.flow.finishStep).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
  });

  it("closes the dialog with the token kept when polling fails", () => {
    setup(throwError(() => new Error("poll failed")));

    expect(host.flow.finishStep).toHaveBeenCalledWith(null);
  });

  it("stops polling once the step is left", () => {
    const poll = new Subject<PiResponse<Tokens>>();
    const fixture = setup(poll);

    fixture.destroy();

    expect(poll.observed).toBe(false);
  });

  it("passes the axe accessibility checks", async () => {
    const fixture = setup();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
