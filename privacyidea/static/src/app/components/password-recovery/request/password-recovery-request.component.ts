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
import { Component, computed, inject, linkedSignal, signal } from "@angular/core";
import { form, FormField, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField, MatInput, MatLabel, MatSuffix } from "@angular/material/input";
import { MatIconModule } from "@angular/material/icon";
import { MatOption, MatSelect } from "@angular/material/select";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { LoginLogoComponent } from "@components/shared/login-logo/login-logo.component";
import { ConfigService } from "@services/config/config.service";
import { RecoverService, RecoverServiceInterface } from "@services/recover/recover.service";

/** Asks for the login name and the email address of the user and has the server email a recovery link. */
@Component({
  selector: "app-password-recovery-request",
  standalone: true,
  imports: [
    FormField,
    LoginLogoComponent,
    MatButtonModule,
    MatFormField,
    MatIconModule,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatSuffix,
    ClearButtonComponent,
    RouterLink
  ],
  templateUrl: "./password-recovery-request.component.html",
  styleUrl: "../../login/login.component.scss"
})
export class PasswordRecoveryRequestComponent {
  private readonly configService = inject(ConfigService);
  private readonly recoverService: RecoverServiceInterface = inject(RecoverService);
  protected readonly loginPath = ROUTE_PATHS.LOGIN;

  username = signal("");
  email = signal("");
  usernameField = form(this.username, (f) => required(f));
  emailField = form(this.email, (f) => required(f));

  realms = computed(() =>
    (this.configService.config()?.realms || "")
      .split(",")
      .map((r: string) => r.trim())
      .filter((r: string) => r)
  );
  realm = linkedSignal({
    source: this.realms,
    computation: (realms) => realms[0] ?? ""
  });

  passwordResetEnabled = computed(() => !!this.configService.config()?.password_reset);
  submitting = signal(false);
  sent = signal(false);
  errorMessage = signal("");

  isSubmitDisabled = computed(() => !this.username() || !this.email() || this.submitting());

  clearRealmSelection(event: MouseEvent): void {
    event.stopPropagation();
    this.realm.set("");
  }

  onSubmit(): void {
    if (this.isSubmitDisabled()) {
      return;
    }
    this.errorMessage.set("");
    this.submitting.set(true);
    const realm = this.realm();
    this.recoverService
      .requestRecoveryCode({ user: this.username(), email: this.email(), ...(realm && realm !== "-" && { realm }) })
      .subscribe({
        next: () => {
          this.submitting.set(false);
          this.sent.set(true);
        },
        error: (err: HttpErrorResponse) => {
          this.submitting.set(false);
          this.errorMessage.set(
            err.error?.result?.error?.message ||
              err.message ||
              $localize`:@@passwordRecovery.requestFailed:The recovery email could not be sent.`
          );
        }
      });
  }
}
