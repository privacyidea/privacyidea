import { NgOptimizedImage, CommonModule } from "@angular/common";
import { Component, effect, ElementRef, inject, signal, ViewChild } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { Router } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { LocalService, LocalServiceInterface } from "../../services/local/local.service";
import { NotificationService, NotificationServiceInterface } from "../../services/notification/notification.service";
import { SessionTimerService, SessionTimerServiceInterface } from "../../services/session-timer/session-timer.service";
import { ValidateService, ValidateServiceInterface } from "../../services/validate/validate.service";
import { ROUTE_PATHS } from "../../app.routes";
import { isAuthenticationSuccessful } from "../../app.component";

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
export class LoginComponent {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router: Router = inject(Router);
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  private readonly validateService: ValidateServiceInterface = inject(ValidateService);

  @ViewChild("otpInput") otpInput!: ElementRef<HTMLInputElement>;

  username = signal<string>("");
  password = signal<string>("");
  otp = signal<string>("");
  loginMessage = signal<string>("");

  showOtpField = signal<boolean>(false);

  constructor() {
    if (this.authService.isAuthenticatedUser()) {
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
    const password = this.password();
    this.loginMessage.set("");

    this.authService
      .authenticate({ username, password })
      .subscribe({
        next: (response) => {
          if (isAuthenticationSuccessful(response)) {
            // The authService's tap operator has already updated the auth state.
            // We just need to store the token and navigate.
            this.localService.saveData(
              this.localService.bearerTokenKey,
              response.result.value.token
            );
            this.showOtpField.set(false);
            this.sessionTimerService.startRefreshingRemainingTime();
            this.sessionTimerService.startTimer();
            this.router.navigateByUrl(ROUTE_PATHS.TOKENS).then();
          } else {
            this.showOtpField.set(true);
            // Use the message from the server if available.
            const message = (response.detail as { message?: string })?.message || "Challenge response required.";
            this.loginMessage.set(message);
          }
        },
        error: (err) => {
          console.error("Authentication error caught in component:", err);
          const message = err.error?.result?.error?.message || "Authentication failed.";
          this.loginMessage.set(message);
          this.password.set("");
        }
      });
  }

  loginPasskey(): void {
    this.loginMessage.set("");
    this.validateService
      .authenticatePasskey()
      .subscribe({
        next: (response) => {
          if (isAuthenticationSuccessful(response)) {
            this.localService.saveData(
              this.localService.bearerTokenKey,
              response.result.value.token
            );
            this.sessionTimerService.startRefreshingRemainingTime();
            this.sessionTimerService.startTimer();
            this.showOtpField.set(false);
            this.router.navigate(["tokens"]).then();
          } else {
            const message = (response.detail as { message?: string })?.message || "Login with passkey failed.";
            this.loginMessage.set(message);
          }
        },
        error: (err: any) => {
          console.error("Error during Passkey login", err);
          const message = err.error?.result?.error?.message || err?.message || "Error during Passkey login";
          this.loginMessage.set(message);
        }
      });
  }

  logout(): void {
    this.localService.removeData(this.localService.bearerTokenKey);
    this.authService.deauthenticate();
    this.router
      .navigate(["login"])
      .then(() => this.notificationService.openSnackBar("Logout successful."));
  }

  resetLogin(): void {
    this.showOtpField.set(false);
    this.loginMessage.set("");
    this.otp.set("");
    // For security, it's good practice to clear the password field.
    this.password.set("");
  }
}
