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
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import {
  TriggerChallengeResponse,
  ValidateCheckDetail,
  ValidateCheckResponse,
  ValidateService
} from "@services/validate/validate.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockNotificationService, MockTokenService, MockValidateService } from "@testing/mock-services";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { map, of, throwError, timer } from "rxjs";
import {
  CONFIRMATION_POLLING_INTERVAL_MS,
  CONFIRMATION_POLLING_TIMEOUT_MS,
  TestOtpPinActionComponent
} from "./test-otp-pin-action.component";

const pushChallenge = MockPiResponse.fromValue<number, TriggerChallengeResponse["detail"]>(1, {
  client_mode: "poll",
  message: "Please confirm the authentication on your mobile device!",
  transaction_id: "4444"
});

function mockValidateCheckResponse(
  authentication: "ACCEPT" | "REJECT" | "CHALLENGE",
  detail: ValidateCheckDetail = {}
): ValidateCheckResponse {
  return {
    id: 1,
    jsonrpc: "2.0",
    detail,
    result: { authentication, status: true },
    signature: "",
    time: Date.now(),
    version: "1.0",
    versionnumber: "1.0"
  };
}

describe("TestOtpPinActionComponent", () => {
  let component: TestOtpPinActionComponent;
  let fixture: ComponentFixture<TestOtpPinActionComponent>;
  let validateService: ValidateService;
  let notificationService: NotificationService;
  let tokenService: TokenService;
  let authService: MockAuthService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TestOtpPinActionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: ValidateService, useClass: MockValidateService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TestOtpPinActionComponent);
    component = fixture.componentInstance;
    validateService = TestBed.inject(ValidateService);
    notificationService = TestBed.inject(NotificationService);
    tokenService = TestBed.inject(TokenService);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("typing into the field updates the model", () => {
    const input: HTMLInputElement = fixture.nativeElement.querySelector("input[matInput]");
    input.value = "654321";
    input.dispatchEvent(new Event("input"));
    expect(component.otpOrPinToTest()).toBe("654321");
  });

  it("the toggle button switches the input between masked and plain text", () => {
    const input: HTMLInputElement = fixture.nativeElement.querySelector("input[matInput]");
    const toggle: HTMLButtonElement = fixture.nativeElement.querySelector("button[matSuffix]");
    expect(input.classList).toContain("masked-input");
    toggle.click();
    fixture.detectChanges();
    expect(component.hide()).toBe(false);
    expect(input.classList).not.toContain("masked-input");
    toggle.click();
    fixture.detectChanges();
    expect(input.classList).toContain("masked-input");
  });

  it("has no password field, so password managers do not offer to save the value", () => {
    const toggle: HTMLButtonElement = fixture.nativeElement.querySelector("button[matSuffix]");
    expect(fixture.nativeElement.querySelector("input[type='password']")).toBeNull();
    expect(fixture.nativeElement.querySelector("input[matInput]").type).toBe("text");

    toggle.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("input[type='password']")).toBeNull();
  });

  it("should test and verify token", () => {
    const testSpy = jest.spyOn(validateService, "testToken");
    component.otpOrPinToTest.set("1234");
    tokenService.tokenSerial.set("Mock serial");

    component.testToken();
    component.verifyOTPValue();

    expect(testSpy).toHaveBeenCalledWith("Mock serial", "1234");
  });

  it("should notify success when the token is accepted", () => {
    jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));

    component.testToken();

    expect(notificationService.success).toHaveBeenCalled();
  });

  it("should notify a warning when the token is rejected", () => {
    jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("REJECT")));

    component.testToken();

    expect(notificationService.warning).toHaveBeenCalled();
  });

  describe("Test without PIN", () => {
    const testWithoutPinButton = (): HTMLButtonElement | undefined =>
      Array.from(fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>).find((button) =>
        button.textContent?.includes("Test without PIN")
      );

    // The rights are no signal, so the view has to be marked for the next check after the mock changes
    const allowTriggerChallenge = (allowed: boolean): void => {
      authService.actionAllowed.mockImplementation((action: string) => allowed && action === "triggerchallenge");
      fixture.componentRef.changeDetectorRef.markForCheck();
      fixture.detectChanges();
    };

    it("hides the button without the triggerchallenge right", () => {
      allowTriggerChallenge(false);
      expect(testWithoutPinButton()).toBeUndefined();
    });

    it("shows the button with the triggerchallenge right", () => {
      allowTriggerChallenge(true);
      expect(testWithoutPinButton()).toBeDefined();
    });

    it("triggers a challenge for the token when the button is clicked", () => {
      allowTriggerChallenge(true);
      tokenService.tokenSerial.set("HOTP0001");

      testWithoutPinButton()?.click();

      expect(validateService.triggerChallenge).toHaveBeenCalledWith("HOTP0001");
      expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    });

    it("opens the challenge with its transaction ID and text", () => {
      component.testWithoutPin();

      expect(component.openChallenge()).toEqual({
        transactionId: "11451135673179897001",
        message: "please enter otp: ",
        waitsForConfirmation: false
      });
      expect(notificationService.success).not.toHaveBeenCalled();
    });

    it("notifies a warning and opens no challenge if the server created no challenge", () => {
      jest
        .spyOn(validateService, "triggerChallenge")
        .mockReturnValue(of(MockPiResponse.fromValue<number, TriggerChallengeResponse["detail"]>(0, {})));

      component.testWithoutPin();

      expect(notificationService.warning).toHaveBeenCalledWith(
        "No challenge triggered. The token must be active and support challenge-response."
      );
      expect(component.openChallenge()).toBeNull();
    });
  });

  describe("open challenge", () => {
    const buttonLabels = (): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll(".actions-pin-button button") as NodeListOf<HTMLElement>).map(
        (button) => button.querySelector(".mdc-button__label")?.textContent?.trim() ?? ""
      );

    beforeEach(() => {
      tokenService.tokenSerial.set("QUST0001");
      component.testWithoutPin();
      fixture.detectChanges();
    });

    it("shows the challenge text, the response field and only the response buttons", () => {
      expect(fixture.nativeElement.querySelector(".challenge-message").textContent).toContain("please enter otp:");
      expect(fixture.nativeElement.querySelector("mat-label").textContent).toContain("Response");
      expect(buttonLabels()).toEqual(["Send Response", "Cancel"]);
    });

    it("sends the response with the transaction ID of the challenge", () => {
      component.otpOrPinToTest.set("test");

      component.sendResponse();

      expect(validateService.testToken).toHaveBeenCalledWith("QUST0001", "test", undefined, "11451135673179897001");
    });

    it("sends the response when Enter is pressed in the response field", () => {
      const input: HTMLInputElement = fixture.nativeElement.querySelector("input[matInput]");
      input.value = "test";
      input.dispatchEvent(new Event("input"));

      input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));

      expect(validateService.testToken).toHaveBeenCalledWith("QUST0001", "test", undefined, "11451135673179897001");
    });

    it("closes the challenge and notifies success if the response is accepted", () => {
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));
      component.otpOrPinToTest.set("test");

      component.sendResponse();
      fixture.detectChanges();

      expect(notificationService.success).toHaveBeenCalledWith("The response was accepted.");
      expect(component.openChallenge()).toBeNull();
      expect(component.otpOrPinToTest()).toBe("");
      expect(buttonLabels()).toContain("Test Token");
    });

    it("keeps the challenge open and notifies a warning if the response is rejected", () => {
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("REJECT")));

      component.sendResponse();

      expect(notificationService.warning).toHaveBeenCalledWith("The response was rejected.");
      expect(component.openChallenge()?.transactionId).toBe("11451135673179897001");
    });

    it("shows the next challenge if the token asks a further question", () => {
      jest
        .spyOn(validateService, "testToken")
        .mockReturnValue(
          of(mockValidateCheckResponse("CHALLENGE", { transaction_id: "2222", message: "What is your pet's name?" }))
        );
      component.otpOrPinToTest.set("test");

      component.sendResponse();

      expect(component.openChallenge()).toEqual({
        transactionId: "2222",
        message: "What is your pet's name?",
        waitsForConfirmation: false
      });
      expect(component.otpOrPinToTest()).toBe("");
    });

    it("ends the test if a policy starts the enrollment of a new token after the accepted response", () => {
      jest.spyOn(validateService, "testToken").mockReturnValue(
        of(
          mockValidateCheckResponse("CHALLENGE", {
            client_mode: "poll",
            enroll_via_multichallenge: true,
            message: "enroll_via_multichallenge_text test",
            serial: "PIPU0001",
            transaction_id: "5555"
          })
        )
      );
      component.otpOrPinToTest.set("test");

      component.sendResponse();

      expect(notificationService.warning).toHaveBeenCalledWith(
        "The response was accepted. A policy then started the enrollment of the token PIPU0001 for the user."
      );
      expect(component.openChallenge()).toBeNull();
      expect(validateService.pollTransactionStatus).not.toHaveBeenCalled();
    });

    it("closes the challenge and clears the field on Cancel", () => {
      component.otpOrPinToTest.set("partial");

      component.cancelChallenge();
      fixture.detectChanges();

      expect(component.openChallenge()).toBeNull();
      expect(component.otpOrPinToTest()).toBe("");
      expect(fixture.nativeElement.querySelector(".challenge-message").textContent.trim()).toBe("");
      expect(fixture.nativeElement.querySelector("mat-label").textContent).toContain("PIN and/or OTP");
    });

    it("refers to the challenge text from the response field", () => {
      const statusRegion: HTMLElement = fixture.nativeElement.querySelector(".challenge-message");
      const input: HTMLInputElement = fixture.nativeElement.querySelector("input[matInput]");

      expect(statusRegion.id).toBeTruthy();
      expect(input.getAttribute("aria-describedby")?.split(" ")).toContain(statusRegion.id);
    });

    it("closes the challenge when the page shows another token", () => {
      tokenService.tokenSerial.set("HOTP0002");

      expect(component.openChallenge()).toBeNull();
    });
  });

  it("opens a challenge if Test Token with the PIN of a challenge-response token returns a challenge", () => {
    jest
      .spyOn(validateService, "testToken")
      .mockReturnValue(of(mockValidateCheckResponse("CHALLENGE", { transaction_id: "3333", message: "Question?" })));

    component.testToken();

    expect(component.openChallenge()).toEqual({
      transactionId: "3333",
      message: "Question?",
      waitsForConfirmation: false
    });
    expect(notificationService.warning).not.toHaveBeenCalled();
  });

  describe("Verify OTP Value", () => {
    const verifyOtpValueButton = (): HTMLButtonElement | undefined =>
      Array.from(fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>).find((button) =>
        button.textContent?.includes("Verify OTP Value")
      );

    it.each(["spass", "push", "question", "indexedsecret", "4eyes", "certificate", "sshkey", "ocra", "tiqr", "u2f"])(
      "hides the button for %s tokens, which the server can not check by the OTP value alone",
      (tokenType) => {
        fixture.componentRef.setInput("tokenType", tokenType);
        fixture.detectChanges();
        expect(verifyOtpValueButton()).toBeUndefined();
      }
    );

    it.each(["hotp", "totp", "motp", "sms", "email", "yubikey", "pw", "registration"])(
      "shows the button for %s tokens",
      (tokenType) => {
        fixture.componentRef.setInput("tokenType", tokenType);
        fixture.detectChanges();
        expect(verifyOtpValueButton()).toBeDefined();
      }
    );

    it("notifies success if the OTP value is accepted", () => {
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));

      component.verifyOTPValue();

      expect(notificationService.success).toHaveBeenCalledWith("The OTP value was accepted.");
    });

    it("notifies a warning if the OTP value is rejected", () => {
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("REJECT")));

      component.verifyOTPValue();

      expect(notificationService.warning).toHaveBeenCalledWith("The OTP value was rejected.");
    });
  });

  describe("challenge with a confirmation on a device", () => {
    beforeEach(() => {
      jest.useFakeTimers();
      tokenService.tokenSerial.set("PIPU0001");
      jest.spyOn(validateService, "triggerChallenge").mockReturnValue(of(pushChallenge));
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("shows the waiting text and only the Cancel button", () => {
      jest.spyOn(validateService, "pollTransactionStatus").mockReturnValue(of("pending"));

      component.testWithoutPin();
      fixture.detectChanges();

      expect(component.openChallenge()?.waitsForConfirmation).toBe(true);
      expect(fixture.nativeElement.querySelector(".challenge-message").textContent).toContain(
        "Waiting for the confirmation on the device."
      );
      expect(fixture.nativeElement.querySelector("input[matInput]")).toBeNull();
      const labels = Array.from(
        fixture.nativeElement.querySelectorAll(".actions-pin-button button") as NodeListOf<HTMLElement>
      ).map((button) => button.querySelector(".mdc-button__label")?.textContent?.trim());
      expect(labels).toEqual(["Cancel"]);
    });

    it("completes the authentication with an empty response after the confirmation", () => {
      const pollTransactionStatus = jest
        .spyOn(validateService, "pollTransactionStatus")
        .mockReturnValueOnce(of("pending"))
        .mockReturnValue(of("accept"));
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));

      component.testWithoutPin();
      jest.advanceTimersByTime(CONFIRMATION_POLLING_INTERVAL_MS);

      expect(pollTransactionStatus).toHaveBeenCalledWith("4444");
      expect(validateService.testToken).toHaveBeenCalledWith("PIPU0001", "", undefined, "4444");
      expect(notificationService.success).toHaveBeenCalledWith("The response was accepted.");
      expect(component.openChallenge()).toBeNull();
    });

    it("waits for a poll that takes longer than the polling interval", () => {
      const slowPoll = timer(CONFIRMATION_POLLING_INTERVAL_MS * 1.5).pipe(map(() => "accept" as const));
      const pollTransactionStatus = jest.spyOn(validateService, "pollTransactionStatus").mockReturnValue(slowPoll);
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));

      component.testWithoutPin();
      jest.advanceTimersByTime(CONFIRMATION_POLLING_INTERVAL_MS * 2);

      expect(pollTransactionStatus).toHaveBeenCalledTimes(1);
      expect(validateService.testToken).toHaveBeenCalledWith("PIPU0001", "", undefined, "4444");
      expect(notificationService.success).toHaveBeenCalledWith("The response was accepted.");
    });

    it("closes the challenge if the server rejects the confirmed challenge", () => {
      jest.spyOn(validateService, "pollTransactionStatus").mockReturnValue(of("accept"));
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("REJECT")));

      component.testWithoutPin();
      jest.advanceTimersByTime(0);

      expect(notificationService.warning).toHaveBeenCalledWith("The response was rejected.");
      expect(component.openChallenge()).toBeNull();
    });

    it.each([
      ["declined" as const, "The challenge was declined on the device."],
      ["cancelled" as const, "The challenge was cancelled on the device."]
    ])("closes the challenge and notifies a warning if the challenge was %s on the device", (status, message) => {
      const pollTransactionStatus = jest.spyOn(validateService, "pollTransactionStatus").mockReturnValue(of(status));

      component.testWithoutPin();
      jest.advanceTimersByTime(CONFIRMATION_POLLING_INTERVAL_MS * 3);

      expect(notificationService.warning).toHaveBeenCalledWith(message);
      expect(component.openChallenge()).toBeNull();
      expect(validateService.testToken).not.toHaveBeenCalled();
      expect(pollTransactionStatus).toHaveBeenCalledTimes(1);
    });

    it("closes the challenge and stops the polling if a poll fails", () => {
      const pollTransactionStatus = jest
        .spyOn(validateService, "pollTransactionStatus")
        .mockReturnValue(throwError(() => new Error("Polling for transaction failed.")));

      component.testWithoutPin();
      jest.advanceTimersByTime(CONFIRMATION_POLLING_INTERVAL_MS * 3);

      expect(component.openChallenge()).toBeNull();
      expect(pollTransactionStatus).toHaveBeenCalledTimes(1);
    });

    it("closes the challenge and notifies a warning if the device does not confirm in time", () => {
      jest.spyOn(validateService, "pollTransactionStatus").mockReturnValue(of("pending"));

      component.testWithoutPin();
      jest.advanceTimersByTime(CONFIRMATION_POLLING_TIMEOUT_MS);

      expect(notificationService.warning).toHaveBeenCalledWith("The device did not confirm the challenge in time.");
      expect(component.openChallenge()).toBeNull();
    });

    it("stops the polling on Cancel", () => {
      const pollTransactionStatus = jest.spyOn(validateService, "pollTransactionStatus").mockReturnValue(of("pending"));
      component.testWithoutPin();
      jest.advanceTimersByTime(0);
      const pollsBeforeCancel = pollTransactionStatus.mock.calls.length;

      component.cancelChallenge();
      jest.advanceTimersByTime(CONFIRMATION_POLLING_INTERVAL_MS * 3);

      expect(pollTransactionStatus.mock.calls.length).toBe(pollsBeforeCancel);
    });
  });

  it("keeps the status region in the page, so screen readers announce the text of a new challenge", () => {
    const statusRegion: HTMLElement = fixture.nativeElement.querySelector(".challenge-message");
    expect(statusRegion.getAttribute("role")).toBe("status");
    expect(statusRegion.textContent?.trim()).toBe("");

    component.testWithoutPin();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".challenge-message")).toBe(statusRegion);
    expect(statusRegion.textContent).toContain("please enter otp:");
  });

  describe("focus", () => {
    const button = (label: string): HTMLButtonElement | undefined =>
      Array.from(
        fixture.nativeElement.querySelectorAll(".actions-pin-button button") as NodeListOf<HTMLButtonElement>
      ).find((candidate) => candidate.textContent?.includes(label));

    const render = async (): Promise<void> => {
      fixture.detectChanges();
      await fixture.whenStable();
    };

    const click = async (label: string): Promise<void> => {
      const target = button(label);
      target?.focus();
      target?.click();
      await render();
    };

    beforeEach(() => {
      authService.actionAllowed.mockImplementation((action: string) => action === "triggerchallenge");
      fixture.componentRef.changeDetectorRef.markForCheck();
      fixture.detectChanges();
    });

    it("moves the focus to the response field when a challenge opens", async () => {
      await click("Test without PIN");

      expect(document.activeElement).toBe(fixture.nativeElement.querySelector("input[matInput]"));
    });

    it("moves the focus to Cancel while the device confirms the challenge", async () => {
      jest.spyOn(validateService, "triggerChallenge").mockReturnValue(of(pushChallenge));
      jest.spyOn(validateService, "pollTransactionStatus").mockReturnValue(of("pending"));

      await click("Test without PIN");

      expect(document.activeElement).toBe(button("Cancel"));
      component.cancelChallenge();
    });

    it("moves the focus to Test Token when the challenge ends", async () => {
      await click("Test without PIN");

      await click("Cancel");

      expect(document.activeElement).toBe(button("Test Token"));
    });

    it("keeps the focus on Verify OTP Value after a test without a challenge", async () => {
      jest.spyOn(validateService, "testToken").mockReturnValue(of(mockValidateCheckResponse("ACCEPT")));

      await click("Verify OTP Value");

      expect(document.activeElement).toBe(button("Verify OTP Value"));
    });

    it("does not move the focus if the admin moved it out of the section", async () => {
      const elementOutsideOfSection = document.createElement("button");
      document.body.appendChild(elementOutsideOfSection);
      elementOutsideOfSection.focus();

      component.testWithoutPin();
      await render();

      expect(document.activeElement).toBe(elementOutsideOfSection);
      elementOutsideOfSection.remove();
    });
  });
});
