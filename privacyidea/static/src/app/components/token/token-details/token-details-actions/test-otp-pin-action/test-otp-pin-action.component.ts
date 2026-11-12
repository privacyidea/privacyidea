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
import {
  afterNextRender,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  Injector,
  input,
  linkedSignal,
  signal,
  untracked,
  viewChild
} from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput, MatSuffix } from "@angular/material/input";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import {
  ValidateCheckDetail,
  ValidateCheckResponse,
  ValidateService,
  ValidateServiceInterface
} from "@services/validate/validate.service";
import { EMPTY, Subscription, timer } from "rxjs";
import { catchError, exhaustMap, filter, switchMap, take, timeout } from "rxjs/operators";

export const CONFIRMATION_POLLING_INTERVAL_MS = 1000;
export const CONFIRMATION_POLLING_TIMEOUT_MS = 5 * 60 * 1000;

let nextChallengeMessageId = 0;

/**
 * Token types that the server can not check by the OTP value alone, so "Verify OTP Value" never gives a result for
 * them. A Simple Pass token has no OTP value and accepts every value. Push, questionnaire, indexed secret, 4 eyes,
 * certificate and SSH key tokens have no OTP check of their own. OCRA and TiQR tokens need the challenge. U2F tokens
 * are deprecated and refuse every authentication. Challenge-response tokens are tested with "Trigger Challenge".
 */
export const TOKEN_TYPES_WITHOUT_OTP_VALUE_CHECK: ReadonlySet<string> = new Set([
  "spass",
  "push",
  "question",
  "indexedsecret",
  "4eyes",
  "certificate",
  "sshkey",
  "ocra",
  "tiqr",
  "u2f",
  "deprecated"
]);

/** A challenge of the token that the admin can answer in the test section. */
export interface OpenChallenge {
  transactionId: string;
  message: string;
  /** The user confirms the challenge on a device, for example with a push token, and the WebUI polls the server. */
  waitsForConfirmation: boolean;
}

interface CheckResultMessages {
  accepted: string;
  rejected: string;
}

@Component({
  selector: "app-test-otp-pin-action",
  imports: [FormField, MatFormField, MatLabel, MatInput, MatSuffix, MatButtonModule, MatIcon],
  templateUrl: "./test-otp-pin-action.component.html",
  styleUrl: "./test-otp-pin-action.component.scss"
})
export class TestOtpPinActionComponent {
  protected readonly showValueLabel = $localize`:@@common.showValue:Show value`;
  protected readonly hideValueLabel = $localize`:@@common.hideValue:Hide value`;
  private readonly validateService: ValidateServiceInterface = inject(ValidateService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly hostElement: ElementRef<HTMLElement> = inject(ElementRef);
  private readonly injector = inject(Injector);
  private readonly valueInput = viewChild("valueInput", { read: ElementRef<HTMLInputElement> });
  private readonly cancelButton = viewChild("cancelButton", { read: ElementRef<HTMLButtonElement> });
  private readonly testTokenButton = viewChild("testTokenButton", { read: ElementRef<HTMLButtonElement> });
  protected readonly challengeMessageId = `test-otp-pin-challenge-message-${nextChallengeMessageId++}`;
  tokenType = input<string>("");
  showVerifyOtpValue = computed(() => !TOKEN_TYPES_WITHOUT_OTP_VALUE_CHECK.has(this.tokenType()));
  hide = signal(true);
  otpOrPinToTest = signal("");
  otpOrPinForm = form(this.otpOrPinToTest);

  /** The open challenge belongs to one token, so it ends when the page shows another token. */
  openChallenge = linkedSignal<string, OpenChallenge | null>({
    source: () => this.tokenService.tokenSerial(),
    computation: () => null
  });

  private confirmationPolling: Subscription | null = null;

  constructor() {
    effect(() => {
      if (!this.openChallenge()) {
        untracked(() => this.stopConfirmationPolling());
      }
    });
    inject(DestroyRef).onDestroy(() => this.stopConfirmationPolling());
  }

  testToken(): void {
    this.validateService.testToken(this.tokenService.tokenSerial(), this.otpOrPinToTest()).subscribe({
      next: (response) =>
        this.evaluateCheckResponse(response, {
          accepted: $localize`:@@token.otpPinTestedToken:OTP or Pin tested with token was accepted.`,
          rejected: $localize`:@@token.otpPinTestedTokenWas:OTP or Pin tested with token was rejected.`
        })
    });
  }

  triggerChallenge(): void {
    this.validateService.triggerChallenge(this.tokenService.tokenSerial()).subscribe({
      next: (response) => {
        if (response.result?.value && response.detail?.transaction_id) {
          this.startChallenge(response.detail);
        } else {
          this.notificationService.warning(
            $localize`:@@token.noChallengeTriggered:No challenge triggered. The token must be active and support challenge-response.`
          );
        }
        this.tokenService.tokenDetailResource.reload();
      }
    });
  }

  verifyOTPValue(): void {
    this.validateService.testToken(this.tokenService.tokenSerial(), this.otpOrPinToTest(), "1").subscribe({
      next: (response) =>
        this.evaluateCheckResponse(response, {
          accepted: $localize`:@@token.otpValueAccepted:The OTP value was accepted.`,
          rejected: $localize`:@@token.otpValueRejected:The OTP value was rejected.`
        })
    });
  }

  sendResponse(): void {
    const challenge = this.openChallenge();
    if (!challenge) {
      return;
    }
    this.validateService
      .testToken(this.tokenService.tokenSerial(), this.otpOrPinToTest(), undefined, challenge.transactionId)
      .subscribe({
        next: (response) => this.evaluateCheckResponse(response, this.responseMessages())
      });
  }

  cancelChallenge(): void {
    this.stopConfirmationPolling();
    this.endChallenge();
  }

  /**
   * ACCEPT ends an open challenge. CHALLENGE starts a new one, for example after the PIN of a challenge-response token
   * or when the token asks a further question. Any other result keeps an open challenge, so the admin can try again.
   * A CHALLENGE from an enroll_via_multichallenge policy follows a successful test, but it belongs to a new token of
   * the user, so the test ends there.
   */
  private evaluateCheckResponse(response: ValidateCheckResponse, messages: CheckResultMessages): void {
    const authentication = response.result?.authentication;
    if (authentication === "CHALLENGE" && response.detail?.enroll_via_multichallenge) {
      this.endChallenge();
      const enrolledSerial = response.detail.serial ?? "";
      this.notificationService.warning(
        `${messages.accepted} ` +
          $localize`:@@token.enrollViaMultichallengeStarted:A policy then started the enrollment of the token ${enrolledSerial}:SERIAL: for the user.`
      );
    } else if (authentication === "CHALLENGE" && response.detail?.transaction_id) {
      this.startChallenge(response.detail);
    } else if (authentication === "ACCEPT") {
      this.endChallenge();
      this.notificationService.success(messages.accepted);
    } else {
      this.notificationService.warning(messages.rejected);
    }
    this.tokenService.tokenDetailResource.reload();
  }

  private startChallenge(detail: ValidateCheckDetail): void {
    const transactionId = detail.transaction_id ?? "";
    const waitsForConfirmation = detail.client_mode === "poll";
    this.otpOrPinToTest.set("");
    this.openChallenge.set({ transactionId, message: detail.message ?? "", waitsForConfirmation });
    this.moveFocusAfterRender(() => (waitsForConfirmation ? this.cancelButton() : this.valueInput()));
    if (waitsForConfirmation) {
      this.startConfirmationPolling(transactionId);
    }
  }

  /** "Test Token" replaces the buttons of the challenge, so it gets the focus when a challenge ends. */
  private endChallenge(): void {
    const challengeWasOpen = this.openChallenge() !== null;
    this.openChallenge.set(null);
    this.otpOrPinToTest.set("");
    if (challengeWasOpen) {
      this.moveFocusAfterRender(() => this.testTokenButton());
    }
  }

  /**
   * The button that the admin used can disappear with the next render, and the focus then goes to the page. So the
   * focus moves to the control that continues the test. If the admin moved the focus out of the section, it stays
   * there.
   */
  private moveFocusAfterRender(target: () => ElementRef<HTMLElement> | undefined): void {
    afterNextRender(
      () => {
        const focusedElement = document.activeElement;
        const focusIsOutsideOfSection =
          focusedElement !== null &&
          focusedElement !== document.body &&
          focusedElement.isConnected &&
          !this.hostElement.nativeElement.contains(focusedElement);
        if (!focusIsOutsideOfSection) {
          target()?.nativeElement.focus();
        }
      },
      { injector: this.injector }
    );
  }

  /**
   * After the confirmation on the device, an empty response with the transaction ID completes the authentication. A new
   * poll starts only after the previous poll returned, so a slow server can still report the confirmation.
   */
  private startConfirmationPolling(transactionId: string): void {
    this.stopConfirmationPolling();
    const tokenSerial = this.tokenService.tokenSerial();
    this.confirmationPolling = timer(0, CONFIRMATION_POLLING_INTERVAL_MS)
      .pipe(
        exhaustMap(() => this.validateService.pollTransactionStatus(transactionId)),
        filter((status) => status !== "pending"),
        take(1),
        timeout(CONFIRMATION_POLLING_TIMEOUT_MS),
        switchMap((status) => {
          if (status === "accept") {
            return this.validateService.testToken(tokenSerial, "", undefined, transactionId);
          }
          this.endChallenge();
          this.notificationService.warning(
            status === "declined"
              ? $localize`:@@token.confirmationDeclined:The challenge was declined on the device.`
              : $localize`:@@token.confirmationCancelled:The challenge was cancelled on the device.`
          );
          return EMPTY;
        }),
        catchError((error: Error) => {
          // The validate service shows the error of a failed request.
          this.endChallenge();
          if (error.name === "TimeoutError") {
            this.notificationService.warning(
              $localize`:@@token.confirmationTimedOut:The device did not confirm the challenge in time.`
            );
          }
          return EMPTY;
        })
      )
      .subscribe({
        next: (response) => {
          this.evaluateCheckResponse(response, this.responseMessages());
          // Nothing is left to confirm, unless the server started a new challenge.
          if (this.openChallenge()?.transactionId === transactionId) {
            this.endChallenge();
          }
        }
      });
  }

  private stopConfirmationPolling(): void {
    this.confirmationPolling?.unsubscribe();
    this.confirmationPolling = null;
  }

  private responseMessages(): CheckResultMessages {
    return {
      accepted: $localize`:@@token.responseAccepted:The response was accepted.`,
      rejected: $localize`:@@token.responseRejected:The response was rejected.`
    };
  }
}
