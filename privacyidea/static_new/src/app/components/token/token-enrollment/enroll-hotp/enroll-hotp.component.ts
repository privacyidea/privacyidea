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
import { Component, computed, effect, forwardRef, inject, input, signal } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { HotpApiPayloadMapper, HotpEnrollmentData } from "@app/mappers/token-api-payload/hotp-token-api-payload.mapper";
import { HOTP_HASHLIB, HOTP_OTP_LENGTH } from "@constants/token.constants";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface HotpEnrollmentOptions extends TokenEnrollmentData {
  type: "hotp";
  generateOnServer: boolean;
  otpLength: number;
  otpKey?: string;
  hashAlgorithm: string;
  twoStepInit?: boolean;
}

@Component({
  selector: "app-enroll-hotp",
  imports: [MatCheckbox, MatSelect, MatOption, MatLabel, MatFormField, MatInput, MatHint, MatError, FormField],
  templateUrl: "./enroll-hotp.component.html",
  styleUrl: "./enroll-hotp.component.scss",
  standalone: true,
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollHotpComponent) }]
})
export class EnrollHotpComponent extends EnrollTokenBase<HotpEnrollmentData> {
  protected readonly enrollmentMapper: HotpApiPayloadMapper = inject(HotpApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);

  readonly otpLengthOptions = [6, 8];
  readonly hashAlgorithmOptions = [
    { value: "sha1", viewValue: "SHA1" },
    { value: "sha256", viewValue: "SHA256" },
    { value: "sha512", viewValue: "SHA512" }
  ];

  enrollmentData = input<HotpEnrollmentData | null>();
  wizard = input<boolean>(false);
  disabled = input<boolean>(false);

  twoStep = computed(() => this.authService.check2Step("hotp"));
  twoStepEnabled = signal<boolean>(false);
  generateOnServer = signal<boolean>(true);
  otpKey = signal<string>("");
  otpLength = signal<number>(6);
  hashAlgorithm = signal<string>("sha1");

  twoStepDisabled = computed(() => this.disabled() || this.twoStep() === "force");
  generateOnServerDisabled = computed(
    () =>
      this.disabled() ||
      this.twoStep() === "force" ||
      (this.twoStep() === "allow" && this.twoStepEnabled()) ||
      this.authService.checkForceServerGenerateOTPKey("hotp")
  );

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length < 16 ? [{ kind: "minlength" }] : []));
    disabled(f, () => this.disabled() || this.generateOnServer() || this.twoStepEnabled());
  });

  otpLengthForm = form(this.otpLength, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[HOTP_OTP_LENGTH]);
  });

  hashAlgorithmForm = form(this.hashAlgorithm, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[HOTP_HASHLIB]);
  });

  constructor() {
    super();

    effect(() => {
      const hashlib = this.authService.rightsWithValues()[HOTP_HASHLIB];
      if (hashlib) this.hashAlgorithm.set(hashlib);
      const otpLengthPolicy = this.authService.rightsWithValues()[HOTP_OTP_LENGTH];
      if (otpLengthPolicy) {
        const parsedLength = parseInt(otpLengthPolicy, 10);
        if (!isNaN(parsedLength)) this.otpLength.set(parsedLength);
      }
    });

    // Force two-step when policy requires it
    effect(() => {
      if (this.twoStep() === "force") {
        this.twoStepEnabled.set(true);
        this.generateOnServer.set(true);
      }
    });

    // Force generateOnServer when policy requires it
    effect(() => {
      if (this.authService.checkForceServerGenerateOTPKey("hotp")) this.generateOnServer.set(true);
    });

    // When twoStep is enabled with "allow" policy, force generateOnServer=true
    effect(() => {
      if (this.twoStep() === "allow" && this.twoStepEnabled()) this.generateOnServer.set(true);
    });

    // Apply initial enrollment data
    effect(() => {
      const data = this.enrollmentData();
      if (data) {
        this.generateOnServer.set(data.generateOnServer ?? true);
        this.otpLength.set(data.otpLength ?? 6);
        this.hashAlgorithm.set(data.hashAlgorithm ?? "sha1");
        if (data.twoStepInit) this.twoStepEnabled.set(data.twoStepInit);
        if (data.otpKey) this.otpKey.set(data.otpKey);
      }
    });
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<HotpEnrollmentData> | null {
    const enrollmentData: HotpEnrollmentOptions = {
      ...basicOptions,
      type: "hotp",
      generateOnServer: this.generateOnServer(),
      otpLength: this.otpLength(),
      hashAlgorithm: this.hashAlgorithm(),
      twoStepInit: this.twoStepEnabled()
    };

    if (!this.generateOnServer()) {
      if (!this.otpKeyForm().valid()) {
        this.otpKeyForm().markAsTouched();
        return null;
      }
      enrollmentData.otpKey = this.otpKey().trim();
    }

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
