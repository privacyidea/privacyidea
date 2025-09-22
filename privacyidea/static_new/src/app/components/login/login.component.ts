/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { CommonModule, NgOptimizedImage } from "@angular/common";
import { Component, computed, effect, ElementRef, inject, OnDestroy, signal, ViewChild } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { Router } from "@angular/router";
import { catchError, EMPTY, filter, Subscription, switchMap, take, timeout, timer } from "rxjs";
import { challengesTriggered, isAuthenticationSuccessful } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthResponse, AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { LocalService, LocalServiceInterface } from "../../services/local/local.service";
import { NotificationService, NotificationServiceInterface } from "../../services/notification/notification.service";
import { SessionTimerService, SessionTimerServiceInterface } from "../../services/session-timer/session-timer.service";
import { ValidateService, ValidateServiceInterface } from "../../services/validate/validate.service";

const PUSH_POLLING_INTERVAL_MS = 500;
const PUSH_POLLING_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

@Component({
  selector: "app-login",
  templateUrl: "./login.component.html",
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormField,
    MatInput,
    MatLabel,
    NgOptimizedImage,
    MatIconModule,
    MatButtonModule
  ],
  styleUrl: "./login.component.scss"
})
export class LoginComponent implements OnDestroy {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router: Router = inject(Router);
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  private readonly validateService: ValidateServiceInterface = inject(ValidateService);
  private transactionId = "";
  private pollingSubscription: Subscription | null = null;
  @ViewChild("otpInput") otpInput!: ElementRef<HTMLInputElement>;
  username = signal<string>("");
  password = signal<string>("");
  otp = signal<string>("");
  loginMessage = signal<string[]>([]);
  errorMessage = signal<string>("");

  showOtpField = signal<boolean>(false);
  pushTriggered = signal<boolean>(false);
  webAuthnTriggered = signal<any | null>(null);

  isLoginButtonDisabled = computed(() => {
    if (this.showOtpField()) {
      // Disable if OTP field is shown but empty
      return !this.otp();
    }
    // Disable if username or password fields are empty
    return !this.username() || !this.password();
  });

  constructor() {
    if (this.authService.isAuthenticated()) {
      console.warn("User is already logged in.");
      this.notificationService.openSnackBar("User is already logged in.");
    } else {
      this.showOtpField.set(false);
    }

    effect(() => {
      if (this.showOtpField()) {
        // Use a timeout to ensure the element is rendered before trying to focus it.
        setTimeout(() => this.otpInput?.nativeElement.focus(), 0);
      }
    });
  }

  onSubmit() {
    const username = this.username();
    const isChallengeResponse = this.showOtpField();
    const password = isChallengeResponse ? this.otp() : this.password();

    const params: any = { username, password };

    if (isChallengeResponse) {
      this.stopPushPolling();
      this.loginMessage.set([]);
      this.errorMessage.set("");
      params.transaction_id = this.transactionId;
    } else {
      this.resetChallengeState();
    }

    this.authService.authenticate(params).subscribe({
      next: (response) => this.evaluateResponse(response, "password"),
      error: (err) => this.handleError(err, "password")
    });
  }

  webAuthnLogin(): void {
    const signRequest = this.webAuthnTriggered();
    if (!signRequest) {
      console.error("WebAuthn sign request not available.");
      return;
    }

    this.validateService
      .authenticateWebAuthn({
        signRequest: signRequest,
        transaction_id: this.transactionId,
        username: this.username()
      })
      .subscribe({
        next: (response: AuthResponse) => this.evaluateResponse(response, "webauthn"),
        error: (err: any) => this.handleError(err, "webauthn")
      });
  }

  passkeyLogin(): void {
    this.validateService.authenticatePasskey().subscribe({
      next: (response) => this.evaluateResponse(response, "passkey"),
      error: (err: any) => this.handleError(err, "passkey")
    });
  }

  logout(): void {
    this.authService.logout();
    this.localService.removeData("bearer_token");
    this.router.navigate(["login"]).then(() => this.notificationService.openSnackBar("Logout successful."));
  }

  resetLogin(): void {
    this.resetChallengeState();
    this.showOtpField.set(false);
    this.otp.set("");
    this.password.set("");
  }

  ngOnDestroy(): void {
    this.stopPushPolling();
  }

  private startPushPolling(): void {
    this.stopPushPolling();

    const poll$ = timer(0, PUSH_POLLING_INTERVAL_MS).pipe(
      switchMap(() => this.validateService.pollTransaction(this.transactionId)),
      filter((success) => success === true),
      take(1),
      timeout(PUSH_POLLING_TIMEOUT_MS),
      catchError((err) => {
        if (err.name === "TimeoutError") {
          this.errorMessage.set("Polling for push notification timed out. Please try again.");
        } else {
          // The error is already handled by the service, just log it here.
          console.error("Error during push polling:", err);
        }
        return EMPTY; // Stop the stream
      })
    );

    this.pollingSubscription = poll$.subscribe({
      next: (success) => {
        if (success) {
          this.authService
            .authenticate({
              username: this.username(),
              password: "",
              transaction_id: this.transactionId
            })
            .subscribe({
              next: (response) => this.evaluateResponse(response, "password"),
              error: (err) => this.handleError(err, "password")
            });
        }
      }
    });
  }

  private stopPushPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
      this.pollingSubscription = null;
    }
  }

  private resetChallengeState(): void {
    this.stopPushPolling();
    this.loginMessage.set([]);
    this.errorMessage.set("");
    this.pushTriggered.set(false);
    this.webAuthnTriggered.set(null);
    this.transactionId = "";
  }

  private evaluateResponse(response: AuthResponse, context: "password" | "passkey" | "webauthn"): void {
    if (isAuthenticationSuccessful(response)) {
      // Successful auth -> log in
      this.localService.saveData("bearer_token", response.result.value.token);
      this.showOtpField.set(false);
      this.sessionTimerService.startRefreshingRemainingTime();
      this.sessionTimerService.startTimer();
      if (this.authService.role() === "user" || this.authService.anyTokenActionAllowed()) {
        this.router.navigateByUrl(ROUTE_PATHS.TOKENS).then();
      } else if (this.authService.anyContainerActionAllowed()) {
        this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS).then();
      } else {
        this.router.navigateByUrl(ROUTE_PATHS.TOKENS).then();
      }

    } else if (challengesTriggered(response)) {
      // Setup depending on what kind of challenges were triggered
      if (response.detail.multi_challenge?.length) {
        this.transactionId = response.detail.transaction_id || "";
        this.pushTriggered.set(response.detail.multi_challenge.some((c) => c.type === "push"));
        const webAuthnChallenge = response.detail.multi_challenge.find((c) => c.type === "webauthn");
        if (webAuthnChallenge?.attributes?.webAuthnSignRequest) {
          this.webAuthnTriggered.set(webAuthnChallenge.attributes.webAuthnSignRequest); // This is now an object
        }
        if (this.pushTriggered()) {
          this.startPushPolling();
        }
      }
      // A password login can result in an OTP challenge, but a passkey login failing just fails.
      if (context === "password") {
        this.showOtpField.set(true);
      }
      const defaultMessages = {
        password: "Challenge response required.",
        passkey: "Login with passkey failed.",
        webauthn: "Login with WebAuthn failed."
      };
      if (response.detail.multi_challenge?.length) {
        this.loginMessage.set([...new Set(response.detail.multi_challenge.map((c) => c.message))]);
      } else {
        const message = response.detail.message || defaultMessages[context];
        this.loginMessage.set([message]);
      }
    } else {
      // fail
      const defaultMessages = {
        password: "Authentication failed.",
        passkey: "Login with passkey failed.",
        webauthn: "Login with WebAuthn failed."
      };
      const message =
        response.result?.error?.message ||
        (
          response.detail as {
            message?: string;
          }
        )?.message ||
        defaultMessages[context];
      this.errorMessage.set(message);
    }
  }

  private handleError(err: any, context: "password" | "passkey" | "webauthn"): void {
    const defaultMessages = {
      password: "Authentication failed.",
      passkey: "Error during Passkey login",
      webauthn: "Error during WebAuthn login"
    };
    const message = err.error?.result?.error?.message || err?.message || defaultMessages[context];
    this.errorMessage.set(message);

    if (context === "password") {
      this.password.set("");
      if (this.showOtpField()) {
        // Empty the value and focus again
        this.otp.set("");
        setTimeout(() => this.otpInput?.nativeElement.focus(), 0);
      }
    }
  }
}
