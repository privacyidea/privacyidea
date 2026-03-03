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

import { Component, computed, inject, input, linkedSignal } from "@angular/core";
import { EnrollTokenArguments, TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import {
  NO_QR_CODE_TOKEN_TYPES,
  NO_REGENERATE_TOKEN_TYPES,
  REGENERATE_AS_VALUES_TOKEN_TYPES
} from "../token-enrollment.constants";
import {
  BaseApiPayloadMapper,
  EnrollmentResponseDetail,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { OtpKeyComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-key/otp-key.component";
import { OtpValuesComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-values/otp-values.component";
import { QrCodeTextComponent } from "@components/token/token-enrollment/token-enrollment-data/qr-code-text/qr-code-text.component";
import { RegistrationCodeComponent } from "@components/token/token-enrollment/token-enrollment-data/registration-code/registration-code.component";
import { TiqrEnrollUrlComponent } from "@components/token/token-enrollment/token-enrollment-data/tiqr-enroll-url/tiqr-enroll-url.component";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";

@Component({
  selector: "app-token-enrollment-data",
  imports: [
    MatButton,
    MatIcon,
    OtpKeyComponent,
    OtpValuesComponent,
    QrCodeTextComponent,
    RegistrationCodeComponent,
    TiqrEnrollUrlComponent
  ],
  standalone: true,
  templateUrl: "./token-enrollment-data.component.html",
  styleUrl: "./token-enrollment-data.component.scss"
})
export class TokenEnrollmentDataComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly Object = Object;
  enrolledInputData = input<EnrollmentResponseDetail>();
  enrollmentParameters = input<EnrollTokenArguments>();
  tokenType = input<string>(this.tokenService.selectedTokenType()?.key);

  enrolledData = linkedSignal(() => this.enrolledInputData());
  protected readonly serial = computed(() => this.enrolledData()?.serial ?? "");
  protected readonly containerSerial = computed(() => this.enrolledData()?.["container_serial"] ?? "");
  protected readonly qrCode = computed(() =>
    this.enrolledData()?.googleurl?.img ??
    this.enrolledData()?.motpurl?.img ??
    this.enrolledData()?.otpkey?.img ??
    this.enrolledData()?.tiqrenroll?.img ??
    "");
  protected readonly url = computed(() =>
    this.enrolledData()?.googleurl?.value ??
    this.enrolledData()?.motpurl?.value ??
    this.enrolledData()?.otpkey?.value ??
    this.enrolledData()?.tiqrenroll?.value ??
    "");
  protected readonly verify_message = computed(() => this.enrolledData()?.verify?.message ?? null);

  showQRCode = computed(() => !NO_QR_CODE_TOKEN_TYPES.includes(this.tokenType()));
  showRegenerateButton = computed(() => !NO_REGENERATE_TOKEN_TYPES.includes(this.tokenType()));
  regenerateButtonText = computed(() =>
    REGENERATE_AS_VALUES_TOKEN_TYPES.includes(this.tokenType()) ? $localize`Regenerate Values` : $localize`Regenerate QR Code`);

  regenerateQRCode() {
    if (!this.enrollmentParameters()) {
      this.notificationService.openSnackBar($localize`Enrollment parameters are missing. Cannot regenerate token.`);
      return;
    }
    const newEnrollmentData: TokenEnrollmentData = {
      ...(this.enrollmentParameters()?.data ?? {} as TokenEnrollmentData)
    };
    const mapper = this.enrollmentParameters()?.mapper ?? new BaseApiPayloadMapper();

    this.tokenService.enrollToken({ data: newEnrollmentData, mapper: mapper }).subscribe({
      next: (response) => {
        if (response?.detail) {
          this.enrolledData.set(response.detail);
        }
      }
    });
  }
}
