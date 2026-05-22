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
import { form, FormField, required } from "@angular/forms/signals";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-verify-enrollment",
  imports: [MatFormField, MatInput, MatLabel, MatButton, MatIcon, FormField],
  templateUrl: "./verify-enrollment.component.html",
  styleUrl: "./verify-enrollment.component.scss"
})
export class VerifyEnrollmentComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  otpValue = signal("");
  otpForm = form(this.otpValue, (f) => {
    required(f);
  });

  verifyOTP() {
    const verifyData: TokenEnrollmentData = {
      serial: this.tokenService.tokenSerial(),
      type: this.tokenService.selectedTokenType().key,
      verify: this.otpValue()
    };
    this.tokenService.verifyToken(verifyData).subscribe({
      next: (response) => {
        this.tokenService.tokenDetailResource.reload();
        if (response?.result?.status && response?.detail?.rollout_state === "enrolled") {
          this.notificationService.success($localize`Token verified successfully!`);
        }
      }
    });
  }
}
