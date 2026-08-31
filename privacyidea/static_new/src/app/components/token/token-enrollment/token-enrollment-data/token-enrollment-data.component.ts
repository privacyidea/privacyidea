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

import { Component, computed, inject, input, linkedSignal, output, signal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { OtpKeyComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-key/otp-key.component";
import { OtpValuesComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-values/otp-values.component";
import { QrCodeTextComponent } from "@components/token/token-enrollment/token-enrollment-data/qr-code-text/qr-code-text.component";
import { RegistrationCodeComponent } from "@components/token/token-enrollment/token-enrollment-data/registration-code/registration-code.component";
import { TiqrEnrollUrlComponent } from "@components/token/token-enrollment/token-enrollment-data/tiqr-enroll-url/tiqr-enroll-url.component";
import {
  NO_QR_CODE_TOKEN_TYPES,
  NO_REGENERATE_TOKEN_TYPES,
  REGENERATE_AS_VALUES_TOKEN_TYPES
} from "@components/token/token-enrollment/token-enrollment.constants";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { EnrollTokenArguments, TokenService, TokenServiceInterface } from "@services/token/token.service";

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
  protected readonly Object = Object;
  enrolledInputData = input.required<EnrollmentResponseDetail>();
  enrollmentParameters = input.required<EnrollTokenArguments>();
  tokenType = input.required<string>();
  enrollmentResponseChange = output<EnrollmentResponse>();

  enrolledData = linkedSignal(() => this.enrolledInputData());
  protected readonly serial = computed(() => this.enrolledData()?.serial ?? "");
  protected readonly containerSerial = computed(() => this.enrolledData()?.["container_serial"] ?? "");
  protected readonly qrCode = computed(
    () =>
      this.enrolledData()?.googleurl?.img ??
      this.enrolledData()?.pushurl?.img ??
      this.enrolledData()?.motpurl?.img ??
      this.enrolledData()?.otpkey?.img ??
      this.enrolledData()?.tiqrenroll?.img ??
      ""
  );
  protected readonly url = computed(
    () =>
      this.enrolledData()?.googleurl?.value ??
      this.enrolledData()?.pushurl?.value ??
      this.enrolledData()?.motpurl?.value ??
      this.enrolledData()?.otpkey?.value ??
      this.enrolledData()?.tiqrenroll?.value ??
      ""
  );
  protected readonly verify_message = computed(() => this.enrolledData()?.verify?.message ?? null);

  showQRCode = computed(() => !NO_QR_CODE_TOKEN_TYPES.includes(this.tokenType()));
  protected readonly hasEnrollmentData = computed(
    () =>
      !!(
        (this.showQRCode() && this.qrCode()) ||
        this.enrolledData()?.["password"] ||
        (this.enrolledData()?.otpkey?.value && !this.enrolledData()?.["otps"] && this.showQRCode()) ||
        this.tokenType() === "tiqr" ||
        this.tokenType() === "registration" ||
        this.enrolledData()?.["otps"]
      )
  );
  // A token waiting for enrollment verification cannot be regenerated: the backend rejects any
  // further /token/init for it until a valid "verify" value is supplied, so offering the button
  // would only ever produce an error.
  protected readonly isVerifyPending = computed(() => this.enrolledData()?.rollout_state === "verify");
  showRegenerateButton = computed(
    () => !NO_REGENERATE_TOKEN_TYPES.includes(this.tokenType()) && !this.isVerifyPending()
  );
  regenerateButtonText = computed(() =>
    REGENERATE_AS_VALUES_TOKEN_TYPES.includes(this.tokenType())
      ? $localize`Regenerate Values`
      : $localize`Regenerate QR Code`
  );

  regenerating = signal(false);

  regenerateQRCode() {
    if (this.regenerating()) {
      return;
    }
    const enrollmentParameters = this.enrollmentParameters();
    // The component instance is reused when the surrounding dialog pages between tokens, so
    // remember which token this request belongs to and drop the response if it is no longer
    // the one on screen.
    const requestedSerial = this.serial() || enrollmentParameters.data.serial;
    const newEnrollmentData: TokenEnrollmentData = {
      ...enrollmentParameters.data,
      serial: requestedSerial,
      // The token already exists, so this call re-initializes it rather than enrolling a new
      // one. Without "rollover" the backend treats the request as the next step of the original
      // enrollment and rejects it - for a two-step enrollment the token is still in "clientwait"
      // and resending "2stepinit" fails. "rollover" resets the rollout state first, so a fresh
      // secret is generated and, for two-step, a new server component is issued.
      rollover: true
    };
    // Regenerating replaces the secret and nothing else. The PIN is deliberately not sent
    // again: the server keeps the existing one when the parameter is absent, and re-submitting
    // it would re-apply it without the PIN policy checks, which the server skips for rollover
    // requests.
    delete newEnrollmentData.pin;

    this.regenerating.set(true);
    this.tokenService.enrollToken({ data: newEnrollmentData, mapper: enrollmentParameters.mapper }).subscribe({
      next: (response) => {
        this.regenerating.set(false);
        if (response?.detail) {
          // The opener keys the update on the serial, so it is always told about the response.
          // Only the displayed data is left alone when the dialog has moved on to another token.
          if (this.serial() === requestedSerial) {
            this.enrolledData.set(response.detail);
          }
          this.enrollmentResponseChange.emit(response);
        }
      },
      error: () => this.regenerating.set(false)
    });
  }
}
