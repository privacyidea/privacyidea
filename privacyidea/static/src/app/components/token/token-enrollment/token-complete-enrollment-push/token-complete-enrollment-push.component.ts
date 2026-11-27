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
import { Component, inject, signal } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { PiResponse } from "@app/app.component";
import { EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { Tokens, TokenService, TokenServiceInterface } from "@services/token/token.service";

// The push QR code. The step ends once the app has registered the token.
@Component({
  selector: "app-token-complete-enrollment-push",
  templateUrl: "./token-complete-enrollment-push.component.html",
  styleUrl: "./token-complete-enrollment-push.component.scss"
})
export class TokenCompleteEnrollmentPushComponent extends EnrollmentStep {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly title = signal($localize`:@@token.takeActionYour:Take Action on Your Authenticator`).asReadonly();
  readonly headerState = "incomplete";
  override readonly deleteWarning = $localize`:@@token.pushDeletedAfterScan:The token is deleted even if the QR code was already scanned.`;

  protected readonly detail = this.data.response?.detail;

  constructor() {
    super();
    const serial = this.detail?.serial;
    if (!serial) {
      return;
    }
    // A reopened dialog checks at once whether the app registered meanwhile.
    this.tokenService
      .pollTokenRolloutState({ tokenSerial: serial, initDelay: this.flow.reopened ? 0 : 5000 })
      .pipe(takeUntilDestroyed())
      .subscribe({
        next: (response) => this.onPoll(response),
        // The token stays, the reopen button polls again.
        error: () => this.flow.finishStep(null)
      });
  }

  private onPoll(response: PiResponse<Tokens>): void {
    const tokens = response.result?.value?.tokens;
    if (tokens?.length === 0) {
      this.notificationService.warning(
        $localize`:@@token.enrollmentTokenGone:The token ${this.detail?.serial}:serial: no longer exists. The enrollment was ended.`
      );
      this.flow.finishStep(ENROLLMENT_CANCELLED);
      return;
    }
    if (!this.data.response) {
      return;
    }
    const rolloutState = tokens?.[0]?.rollout_state ?? this.data.response.detail.rollout_state;
    if (rolloutState === "clientwait") {
      return;
    }
    this.flow.finishStep({
      ...this.data.response,
      detail: { ...this.data.response.detail, rollout_state: rolloutState }
    });
  }
}
