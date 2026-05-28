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
import { Component, computed, effect, inject, input, Input, linkedSignal, OnInit, signal, output } from '@angular/core';
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  DaypasswordApiPayloadMapper,
  DaypasswordEnrollmentData
} from "@app/mappers/token-api-payload/daypassword-token-api-payload.mapper";
import { DAYPASSWORD_HASHLIB, DAYPASSWORD_OTP_LENGTH, DAYPASSWORD_TIME_STEP } from "@constants/token.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface DaypasswordEnrollmentOptions extends TokenEnrollmentData {
  type: "daypassword";
  otpKey?: string;
  otpLength: number;
  hashAlgorithm: string;
  timeStep: string;
  generateOnServer: boolean;
}

@Component({
  selector: "app-enroll-daypassword",
  standalone: true,
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatHint,
    MatError,
    MatCheckbox,
    FormField
  ],
  templateUrl: "./enroll-daypassword.component.html",
  styleUrl: "./enroll-daypassword.component.scss"
})
export class EnrollDaypasswordComponent implements OnInit {
  protected readonly enrollmentMapper: DaypasswordApiPayloadMapper = inject(DaypasswordApiPayloadMapper);
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

  enrollmentData = input<DaypasswordEnrollmentData>();
  @Input() wizard = false;
  additionalFormFieldsChange = output<Record<string, unknown>>();
  enrollmentArgsGetterChange = output<(basicOptions: TokenEnrollmentData) => {
      data: DaypasswordEnrollmentData;
      mapper: DaypasswordApiPayloadMapper;
    } | null>();
  disabled = input<boolean>(false);

  generateOnServer = signal<boolean>(true);
  otpKey = signal<string>("");
  otpLength = signal<number>(6);

  defaultHashlib = computed(() => this.systemService.systemConfig()[DAYPASSWORD_HASHLIB] || "sha1");
  defaultTimeStep = computed(() => this.systemService.systemConfig()[DAYPASSWORD_TIME_STEP] || "24h");

  hashAlgorithm = linkedSignal<string>(() => this.defaultHashlib());
  timeStep = linkedSignal<string>(() => this.defaultTimeStep());

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length < 16 ? [{ kind: "minlength" as any }] : []));
    disabled(f, () => this.disabled() || this.generateOnServer() || this.authService.checkForceServerGenerateOTPKey("daypassword"));
  });

  otpLengthForm = form(this.otpLength, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[DAYPASSWORD_OTP_LENGTH]);
  });

  hashAlgorithmForm = form(this.hashAlgorithm, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[DAYPASSWORD_HASHLIB]);
  });

  timeStepForm = form(this.timeStep, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !!this.authService.rightsWithValues()[DAYPASSWORD_TIME_STEP]);
  });

  constructor() {
    // Apply policy defaults when rights load
    effect(() => {
      const hashlib = this.authService.rightsWithValues()[DAYPASSWORD_HASHLIB];
      if (hashlib) this.hashAlgorithm.set(hashlib);
      const otpLengthPolicy = this.authService.rightsWithValues()[DAYPASSWORD_OTP_LENGTH];
      if (otpLengthPolicy) {
        const parsedLength = parseInt(otpLengthPolicy, 10);
        if (!isNaN(parsedLength)) this.otpLength.set(parsedLength);
      }
      const timeStepPolicy = this.authService.rightsWithValues()[DAYPASSWORD_TIME_STEP];
      if (timeStepPolicy) this.timeStep.set(timeStepPolicy);
    });

    // Force generateOnServer when policy requires it
    effect(() => {
      if (this.authService.checkForceServerGenerateOTPKey("daypassword")) this.generateOnServer.set(true);
    });

    // Apply initial enrollment data
    effect(() => {
      const data = this.enrollmentData();
      if (data) {
        this.generateOnServer.set(data.generateOnServer ?? true);
        this.otpLength.set(data.otpLength ?? 6);
        this.hashAlgorithm.set(data.hashAlgorithm ?? "sha256");
        this.timeStep.set(data.timeStep ?? "24h");
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
    data: DaypasswordEnrollmentData;
    mapper: DaypasswordApiPayloadMapper;
  } | null => {
    if (!this.generateOnServer() && !this.otpKeyForm().valid()) {
      this.otpKeyForm().markAsTouched();
      return null;
    }
    const enrollmentData: DaypasswordEnrollmentOptions = {
      ...basicOptions,
      type: "daypassword",
      otpLength: this.otpLength(),
      hashAlgorithm: this.hashAlgorithm(),
      timeStep: this.timeStep(),
      generateOnServer: this.generateOnServer()
    };
    if (!this.generateOnServer()) {
      enrollmentData.otpKey = this.otpKey();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
