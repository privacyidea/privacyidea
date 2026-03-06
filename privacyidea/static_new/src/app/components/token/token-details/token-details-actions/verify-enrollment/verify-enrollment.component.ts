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

import { Component, inject } from "@angular/core";
import { TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../../services/notification/notification.service";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { TokenEnrollmentData } from "../../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { MatFormField, MatInput, MatLabel } from "@angular/material/input";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: 'app-verify-enrollment',
  imports: [
    FormsModule,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    MatButton,
    MatIcon
  ],
  templateUrl: './verify-enrollment.component.html',
  styleUrl: './verify-enrollment.component.scss'
})
export class VerifyEnrollmentComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  otpControl = new FormControl("", { nonNullable: true, validators: [Validators.required] });

  verifyOTP() {
    const verifyData: TokenEnrollmentData = {
      serial: this.tokenService.tokenSerial(),
      type: this.tokenService.selectedTokenType().key,
      verify: this.otpControl.value
    };
    this.tokenService.verifyToken(verifyData).subscribe({
      next: (response) => {
        this.tokenService.tokenDetailResource.reload();
        if (response?.result?.status && response?.detail?.rollout_state === "enrolled") {
          this.notificationService.openSnackBar($localize`Token verified successfully!`);
        }
      }
    });
  }
}
