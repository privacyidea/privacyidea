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

import { Component, computed, effect, inject, input, linkedSignal, output, signal } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { ApplspecEnrollmentData } from "@app/mappers/token-api-payload/applspec-token-api-payload.mapper";
import { CertificateDataComponent } from "@components/token/token-enrollment/token-enrollment-data/certificate-data/certificate-data.component";
import { EnrollmentSecretComponent } from "@components/token/token-enrollment/token-enrollment-data/enrollment-secret/enrollment-secret.component";
import { OtpKeyComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-key/otp-key.component";
import { OtpValuesComponent } from "@components/token/token-enrollment/token-enrollment-data/otp-values/otp-values.component";
import { QrCodeTextComponent } from "@components/token/token-enrollment/token-enrollment-data/qr-code-text/qr-code-text.component";
import { SavedValues } from "@components/token/token-enrollment/token-enrollment-data/saved-values";
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
    CertificateDataComponent,
    EnrollmentSecretComponent,
    OtpKeyComponent,
    OtpValuesComponent,
    QrCodeTextComponent,
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
  // Without the QR code's text, the regenerate button and the hints to save secrets, for the wizard.
  compact = input<boolean>(false);
  // Set while another request for the token runs, which a regenerate request would cross.
  regenerateDisabled = input<boolean>(false);
  enrollmentResponseChange = output<EnrollmentResponse>();
  unsavedDataChange = output<string>();
  closeConfirmationChange = output<string>();

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
  protected readonly isCertificate = computed(() => this.tokenType() === "certificate");
  protected readonly certificate = computed(() => (this.enrolledData()?.["certificate"] as string) ?? "");
  protected readonly pkcs12 = computed(() => (this.enrolledData()?.["pkcs12"] as string) ?? "");
  protected readonly pkcs12Password = computed(() => (this.enrolledData()?.["pkcs12_password"] as string) ?? "");
  protected readonly registrationCode = computed(() => (this.enrolledData()?.["registrationcode"] as string) ?? "");
  protected readonly password = computed(() => (this.enrolledData()?.["password"] as string) ?? "");
  // A password typed in by the enrolling user is known already, so only a generated one has to be saved.
  protected readonly passwordGenerated = computed(
    () => !!this.password() && (this.enrollmentParameters().data as ApplspecEnrollmentData).generateOnServer !== false
  );
  protected readonly otpValues = computed(() => this.enrolledData()?.["otps"] ?? []);

  protected readonly registrationCodeLabel = $localize`:@@token.registrationCode:Registration Code`;
  protected readonly registrationCodeHint = $localize`:@@token.registrationCodeOnce:Save the registration code now. It is shown here only once and cannot be retrieved again.`;
  protected readonly passwordLabel = $localize`:@@common.password:Password`;
  protected readonly passwordHint = $localize`:@@token.passwordOnce:Save the password now. It is shown here only once and cannot be retrieved again.`;

  // Revealed or copied secrets and printed OTP values.
  private readonly saved = new SavedValues();
  private readonly otpValuesKey = computed(() => `otps:${JSON.stringify(this.otpValues())}`);
  private readonly registrationCodeSaved = computed(() => this.saved.has(`registration:${this.registrationCode()}`));
  private readonly passwordSaved = computed(() => this.saved.has(`password:${this.password()}`));
  private readonly otpValuesPrinted = computed(() => this.saved.has(this.otpValuesKey()));
  private readonly certificateUnsaved = signal("");
  private readonly certificateCloseConfirmation = signal("");

  private readonly registrationCodeOpen = computed(() => !!this.registrationCode() && !this.registrationCodeSaved());
  private readonly passwordOpen = computed(() => this.passwordGenerated() && !this.passwordSaved());
  // The token whose values are being regenerated: the printed ones stop counting, the new ones are not shown yet.
  private readonly regeneratingSerial = signal("");
  private readonly otpValuesOpen = computed(
    () =>
      Object.keys(this.otpValues()).length > 0 &&
      (!this.otpValuesPrinted() || this.regeneratingSerial() === this.serial())
  );

  // What has not been downloaded or saved yet; the wizard asks before it leaves.
  private readonly unsavedData = computed(() =>
    [
      this.certificateUnsaved(),
      this.registrationCodeOpen()
        ? $localize`:@@token.pendingRegistrationCode:Show or copy the registration code.`
        : "",
      this.passwordOpen() ? $localize`:@@token.pendingPassword:Show or copy the password.` : "",
      this.otpValuesOpen() ? $localize`:@@token.pendingOtpValues:Print the OTP values.` : ""
    ]
      .filter(Boolean)
      .join(" ")
  );
  // What closing would lose for good, so the dialog asks first.
  private readonly closeConfirmation = computed(() =>
    [
      this.certificateCloseConfirmation(),
      this.registrationCodeOpen()
        ? $localize`:@@token.closeLosesRegistrationCode:The registration code is shown only once. If you close this dialog now, it cannot be retrieved again.`
        : "",
      this.passwordOpen()
        ? $localize`:@@token.closeLosesPassword:The password is shown only once. If you close this dialog now, it cannot be retrieved again.`
        : "",
      this.otpValuesOpen()
        ? $localize`:@@token.closeLosesOtpValues:The OTP values are shown only once. If you close this dialog now without printing them, they cannot be retrieved again.`
        : ""
    ]
      .filter(Boolean)
      .join(" ")
  );

  showQRCode = computed(() => !NO_QR_CODE_TOKEN_TYPES.includes(this.tokenType()));
  // A token waiting for enrollment verification cannot be regenerated: the backend rejects any
  // further /token/init for it until a valid "verify" value is supplied, so offering the button
  // would only ever produce an error.
  protected readonly isVerifyPending = computed(() => this.enrolledData()?.rollout_state === "verify");
  showRegenerateButton = computed(
    () => !this.compact() && !NO_REGENERATE_TOKEN_TYPES.includes(this.tokenType()) && !this.isVerifyPending()
  );
  regenerateButtonText = computed(() =>
    REGENERATE_AS_VALUES_TOKEN_TYPES.includes(this.tokenType())
      ? $localize`:@@token.regenerateValues:Regenerate Values`
      : $localize`:@@common.regenerateQrCode:Regenerate QR Code`
  );

  regenerating = signal(false);

  constructor() {
    // Also reported again for another token with the same message, since a dialog that pages between tokens records it
    // per token.
    effect(() => {
      this.serial();
      this.unsavedDataChange.emit(this.unsavedData());
    });
    effect(() => {
      this.serial();
      this.closeConfirmationChange.emit(this.closeConfirmation());
    });
  }

  onRegistrationCodeSaved(): void {
    this.saved.add(`registration:${this.registrationCode()}`);
  }

  onPasswordSaved(): void {
    this.saved.add(`password:${this.password()}`);
  }

  onOtpValuesPrinted(): void {
    this.saved.add(this.otpValuesKey());
  }

  onCertificateUnsavedChange(unsaved: string): void {
    this.certificateUnsaved.set(unsaved);
  }

  onCertificateCloseConfirmationChange(message: string): void {
    this.certificateCloseConfirmation.set(message);
  }

  regenerateQRCode() {
    if (this.regenerating() || this.regenerateDisabled()) {
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
    this.regeneratingSerial.set(this.serial());
    this.tokenService.enrollToken({ data: newEnrollmentData, mapper: enrollmentParameters.mapper }).subscribe({
      next: (response) => {
        this.regenerating.set(false);
        this.regeneratingSerial.set("");
        if (response?.detail) {
          // The opener keys the update on the serial, so it is always told about the response.
          // Only the displayed data is left alone when the dialog has moved on to another token.
          if (this.serial() === requestedSerial) {
            this.enrolledData.set(response.detail);
          }
          this.enrollmentResponseChange.emit(response);
        }
      },
      error: () => {
        this.regenerating.set(false);
        this.regeneratingSerial.set("");
      }
    });
  }
}
