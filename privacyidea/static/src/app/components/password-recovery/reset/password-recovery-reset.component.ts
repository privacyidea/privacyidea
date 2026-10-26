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
import { HttpErrorResponse } from "@angular/common/http";
import { Component, computed, inject, signal } from "@angular/core";
import { form, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { LoginLogoComponent } from "@components/shared/login-logo/login-logo.component";
import { MaskedInputComponent } from "@components/shared/masked-input/masked-input.component";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { RecoverService, RecoverServiceInterface } from "@services/recover/recover.service";

/**
 * Splits the `<login name>@<realm>` of the link in the recovery email. The login name can contain an "@" itself, the
 * realm cannot.
 */
export function splitUserAndRealm(userAndRealm: string): { user: string; realm?: string } {
  const separator = userAndRealm.lastIndexOf("@");
  if (separator < 1) {
    return { user: userAndRealm };
  }
  return { user: userAndRealm.slice(0, separator), realm: userAndRealm.slice(separator + 1) };
}

/** The page the link in the recovery email opens: asks for the new password and sets it with the recovery code. */
@Component({
  selector: "app-password-recovery-reset",
  standalone: true,
  imports: [LoginLogoComponent, MaskedInputComponent, MatButtonModule, MatIconModule, RouterLink],
  templateUrl: "./password-recovery-reset.component.html",
  styleUrl: "../../login/login.component.scss"
})
export class PasswordRecoveryResetComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly recoverService: RecoverServiceInterface = inject(RecoverService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly loginPath = ROUTE_PATHS.LOGIN;

  private readonly recoveryCode = this.route.snapshot.paramMap.get("code") ?? "";
  protected readonly account = splitUserAndRealm(this.route.snapshot.paramMap.get("user") ?? "");

  password = signal("");
  repeatPassword = signal("");
  passwordField = form(this.password, (f) => required(f));
  repeatPasswordField = form(this.repeatPassword, (f) => required(f));

  submitting = signal(false);
  errorMessage = signal("");

  passwordMismatch = computed(() => this.repeatPassword() !== "" && this.repeatPassword() !== this.password());
  mismatchMessage = computed(() =>
    this.passwordMismatch() ? $localize`:@@passwordRecovery.passwordsDoNotMatch:The passwords do not match.` : ""
  );
  isSubmitDisabled = computed(() => !this.password() || this.password() !== this.repeatPassword() || this.submitting());

  onSubmit(): void {
    if (this.isSubmitDisabled()) {
      return;
    }
    this.errorMessage.set("");
    this.submitting.set(true);
    this.recoverService
      .resetPassword({ ...this.account, recoverycode: this.recoveryCode, password: this.password() })
      .subscribe({
        next: (response) => {
          this.submitting.set(false);
          if (response.result?.value) {
            this.notificationService.success(
              $localize`:@@passwordRecovery.passwordChanged:Your password has been changed. You can log in now.`
            );
            void this.router.navigateByUrl(ROUTE_PATHS.LOGIN);
          } else {
            this.errorMessage.set(
              $localize`:@@passwordRecovery.invalidCode:The link is invalid or has expired. Please request a new one.`
            );
          }
        },
        error: (err: HttpErrorResponse) => {
          this.submitting.set(false);
          this.errorMessage.set(
            err.error?.result?.error?.message ||
              err.message ||
              $localize`:@@passwordRecovery.resetFailed:The password could not be changed.`
          );
        }
      });
  }
}
