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

import { Component, inject, Input, input, WritableSignal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatDivider } from "@angular/material/divider";
import { MatIconModule } from "@angular/material/icon";
import { ResyncTokenActionComponent } from "@components/token/token-details/token-details-actions/resync-token-action/resync-token-action.component";
import { TestPasskeyActionComponent } from "@components/token/token-details/token-details-actions/test-passkey-action/test-passkey-action.component";
import { SetPinActionComponent } from "@components/token/token-details/token-details-actions/set-pin-action/set-pin-action.component";
import { TestOtpPinActionComponent } from "@components/token/token-details/token-details-actions/test-otp-pin-action/test-otp-pin-action.component";
import { VerifyEnrollmentComponent } from "@components/token/token-details/token-details-actions/verify-enrollment/verify-enrollment.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { TokenDetails } from "@services/token/token.service";

@Component({
  selector: "app-token-details-actions",
  standalone: true,
  imports: [
    MatButtonModule,
    MatDivider,
    MatIconModule,
    SetPinActionComponent,
    ResyncTokenActionComponent,
    TestOtpPinActionComponent,
    TestPasskeyActionComponent,
    VerifyEnrollmentComponent
  ],
  templateUrl: "./token-details-actions.component.html",
  styleUrl: "./token-details-actions.component.scss"
})
export class TokenDetailsActionsComponent {
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  @Input({ required: true }) tokenType!: WritableSignal<string>;
  token = input<TokenDetails>();

  protected get hasAnyAction(): boolean {
    const type = this.tokenType?.();
    const isVerify = this.token()?.rollout_state === "verify";
    const nonWebauthn = type !== "passkey" && type !== "webauthn";
    return (
      isVerify ||
      type === "passkey" ||
      nonWebauthn ||
      this.authService.actionAllowed("setpin") ||
      this.authService.actionsAllowed(["setrandompin", "otp_pin_set_random"])
    );
  }
}
