import { NgOptimizedImage } from "@angular/common";
import { Component, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatFabButton } from "@angular/material/button";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../app.routes";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { LocalService, LocalServiceInterface } from "../../services/local/local.service";
import { NotificationService, NotificationServiceInterface } from "../../services/notification/notification.service";
import { SessionTimerService, SessionTimerServiceInterface } from "../../services/session-timer/session-timer.service";
import { ValidateService, ValidateServiceInterface } from "../../services/validate/validate.service";

@Component({
  selector: "app-login",
  templateUrl: "./login.component.html",
  standalone: true,
  imports: [FormsModule, MatFormField, MatInput, MatLabel, NgOptimizedImage, MatIconModule, MatFabButton],
  styleUrl: "./login.component.scss"
})
export class LoginComponent {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router: Router = inject(Router);
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  private readonly validateService: ValidateServiceInterface = inject(ValidateService);

  username = signal<string>("");
  password = signal<string>("");

  constructor() {
    if (this.authService.isAuthenticated()) {
      console.warn("User is already logged in.");
      this.notificationService.openSnackBar("User is already logged in.");
    }
  }

  onSubmit() {
    const username = this.username();
    const password = this.password();

    this.authService.authenticate({ username, password }).subscribe({
      next: (response) => {
        if (
          response.result &&
          response.result?.value &&
          response.result?.value.token &&
          this.authService.isAuthenticated()
        ) {
          this.sessionTimerService.startRefreshingRemainingTime();
          this.sessionTimerService.startTimer();
          this.router.navigateByUrl(ROUTE_PATHS.TOKENS);
        } else {
          console.error("Login failed. Challenge response required.");
          this.notificationService.openSnackBar("Login failed. Challenge response required.");
        }
      }
    });
  }

  logout(): void {
    this.localService.removeData(this.authService.TOKEN_KEY);
    this.authService.deauthenticate();
    this.router.navigate(["login"]).then(() => this.notificationService.openSnackBar("Logout successful."));
  }

  loginPasskey(): void {
    this.validateService.authenticatePasskey().subscribe({
      next: (response) => {
        if (
          response.result &&
          response.result.value &&
          response.result.value.token &&
          this.authService.isAuthenticated()
        ) {
          this.localService.saveData(this.authService.TOKEN_KEY, response.result?.value.token);
          this.sessionTimerService.startRefreshingRemainingTime();
          this.sessionTimerService.startTimer();
          this.router.navigate(["tokens"]).then();
          this.notificationService.openSnackBar("Login successful.");
        } else {
          this.notificationService.openSnackBar("Login with passkey failed.");
        }
      },
      error: (err: any) => {
        console.error("Error during Passkey login", err);
        this.notificationService.openSnackBar(err?.message || "Error during Passkey login");
      }
    });
  }
}
