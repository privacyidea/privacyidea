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

import { Component, computed, inject, Input, input } from "@angular/core";
import { TokenService, TokenServiceInterface, TokenTypeKey } from "../../../../services/token/token.service";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";
import { FormControl, Validators } from "@angular/forms";
import {
  NO_QR_CODE_TOKEN_TYPES,
  NO_REGENERATE_TOKEN_TYPES,
  REGENERATE_AS_VALUES_TOKEN_TYPES
} from "../token-enrollment.constants";
import {
  EnrollmentResponseDetail,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { OtpKeyComponent } from "../token-enrollment-last-step-dialog/otp-key/otp-key.component";
import { OtpValuesComponent } from "../token-enrollment-last-step-dialog/otp-values/otp-values.component";
import { QrCodeTextComponent } from "../token-enrollment-last-step-dialog/qr-code-text/qr-code-text.component";
import { RegistrationCodeComponent } from "../token-enrollment-last-step-dialog/registration-code/registration-code.component";
import { TiqrEnrollUrlComponent } from "../token-enrollment-last-step-dialog/tiqr-enroll-url/tiqr-enroll-url.component";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { NgOptimizedImage } from "@angular/common";

@Component({
  selector: "app-token-enrollment-data",
  imports: [
    MatButton,
    MatIcon,
    OtpKeyComponent,
    OtpValuesComponent,
    QrCodeTextComponent,
    RegistrationCodeComponent,
    TiqrEnrollUrlComponent,
    NgOptimizedImage
  ],
  standalone: true,
  templateUrl: "./token-enrollment-data.component.html",
  styleUrl: "./token-enrollment-data.component.scss"
})
export class TokenEnrollmentDataComponent {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly Object = Object;
  enrolledData = input<EnrollmentResponseDetail>();
  enrollmentParameters = input<TokenEnrollmentData>();
  tokenType = input<string>(this.tokenService.selectedTokenType()?.key);

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
  verifyOTPControl = new FormControl("", { nonNullable: true });

  showQRCode = computed(() => !NO_QR_CODE_TOKEN_TYPES.includes(this.tokenType()));
  showRegenerateButton = computed(() => !NO_REGENERATE_TOKEN_TYPES.includes(this.tokenType()));
  regenerateButtonText = computed(() =>
    REGENERATE_AS_VALUES_TOKEN_TYPES.includes(this.tokenType()) ? "Values" : "QR" + " Code");

  regenerateQRCode() {
    // TODO
    // this.data.serial.set(this.data.response.detail?.serial ?? null);
    // this.data.enrollToken();
    // this.data.serial.set(null);
    // this.dialogRef.close();

    if (!this.enrollmentParameters()) {
      // TODO: Handle this case
    }
    if (!this.enrollmentParameters()?.serial) {
      this.enrollmentParameters
    }
    const newEnrollmentData = {
      ...(this.enrollmentParameters() ?? {}),
      ...(this.enrollmentParameters()?.serial && { serial: this.enrollmentParameters()?.serial })
    }

    // this.tokenService.enrollToken(newEnrollmentData);
  }
}
