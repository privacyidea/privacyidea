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
import { Component, computed, effect, EventEmitter, inject, input, OnInit, Output, signal } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { TotpApiPayloadMapper, TotpEnrollmentData } from "@app/mappers/token-api-payload/totp-token-api-payload.mapper";
import { TOTP_HASHLIB, TOTP_OTP_LENGTH, TOTP_TIME_STEP } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface TotpEnrollmentOptions extends TokenEnrollmentData {
  type: "totp";
  generateOnServer: boolean;
  otpLength: number;
  otpKey?: string;
  hashAlgorithm: string;
  timeStep: number;
  twoStepInit?: boolean;
}

@Component({
  selector: "app-enroll-totp",
  standalone: true,
  imports: [MatCheckbox, MatFormField, MatHint, MatInput, MatLabel, MatOption, MatSelect, MatError, FormField],
  templateUrl: "./enroll-totp.component.html",
  styleUrl: "./enroll-totp.component.scss"
})
export class EnrollTotpComponent implements OnInit {
  protected readonly enrollmentMapper = inject(TotpApiPayloadMapper);
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
  readonly timeStepOptions = [30, 60];

  enrollmentData = input<TotpEnrollmentData>();
  wizard = input(false);
  @Output() additionalFormFieldsChange = new EventEmitter<Record<string, unknown>>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: TotpEnrollmentData;
      mapper: TokenApiPayloadMapper<TotpEnrollmentData>;
    } | null
  >();
  disabled = input<boolean>(false);

  twoStep = computed(() => this.authService.check2Step("totp"));
  twoStepEnabled = signal<boolean>(false);
  generateOnServer = signal<boolean>(true);
  otpKey = signal<string>("");
  otpLength = signal<number>(6);
  hashAlgorithm = signal<string>("sha1");
  timeStep = signal<number>(30);

  twoStepDisabled = computed(() => this.disabled() || this.twoStep() === "force");
  generateOnServerDisabled = computed(
    () =>
      this.disabled() ||
      this.twoStep() === "force" ||
      (this.twoStep() === "allow" && this.twoStepEnabled()) ||
      this.authService.checkForceServerGenerateOTPKey("totp")
  );

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length < 16 ? [{ kind: "minlength" }] : []));
    disabled(f, () => this.disabled() || this.generateOnServer() || this.twoStepEnabled());
  });

  otpLengthForm = form(this.otpLength, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[TOTP_OTP_LENGTH]);
  });

  hashAlgorithmForm = form(this.hashAlgorithm, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[TOTP_HASHLIB]);
  });

  timeStepForm = form(this.timeStep, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[TOTP_TIME_STEP]);
  });

  constructor() {
    // Apply policy defaults when rights load
    effect(() => {
      const hashlib = this.authService.rightsWithValues()[TOTP_HASHLIB];
      if (hashlib) this.hashAlgorithm.set(hashlib);
      const otpLengthPolicy = this.authService.rightsWithValues()[TOTP_OTP_LENGTH];
      if (otpLengthPolicy) {
        const parsedLength = parseInt(otpLengthPolicy, 10);
        if (!isNaN(parsedLength)) this.otpLength.set(parsedLength);
      }
      const timeStepPolicy = this.authService.rightsWithValues()[TOTP_TIME_STEP];
      if (timeStepPolicy) {
        const parsedTimeStep = parseInt(timeStepPolicy, 10);
        if (!isNaN(parsedTimeStep)) this.timeStep.set(parsedTimeStep);
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
      if (this.authService.checkForceServerGenerateOTPKey("totp")) this.generateOnServer.set(true);
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
        if (data.timeStep) this.timeStep.set(data.timeStep);
        if (data.twoStepInit) this.twoStepEnabled.set(data.twoStepInit);
        if (data.otpKey) this.otpKey.set(data.otpKey);
      }
    });
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: TotpEnrollmentData;
    mapper: TokenApiPayloadMapper<TotpEnrollmentData>;
  } | null => {
    const enrollmentData: TotpEnrollmentOptions = {
      ...basicOptions,
      type: "totp",
      generateOnServer: this.generateOnServer(),
      otpLength: this.otpLength(),
      hashAlgorithm: this.hashAlgorithm(),
      timeStep: this.timeStep(),
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
  };
}
