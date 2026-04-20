/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, computed, effect, EventEmitter, inject, input, Input, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  TotpApiPayloadMapper,
  TotpEnrollmentData
} from "../../../../mappers/token-api-payload/totp-token-api-payload.mapper";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { TOTP_HASHLIB, TOTP_OTP_LENGTH, TOTP_TIME_STEP } from "../../../../constants/token.constants";

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
  imports: [
    FormsModule,
    MatCheckbox,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatError,
    ReactiveFormsModule
  ],
  templateUrl: "./enroll-totp.component.html",
  styleUrl: "./enroll-totp.component.scss"
})
export class EnrollTotpComponent implements OnInit {
  protected readonly enrollmentMapper: TotpApiPayloadMapper = inject(TotpApiPayloadMapper);
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
  @Input() wizard: boolean = false;
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: TotpEnrollmentData;
      mapper: TokenApiPayloadMapper<TotpEnrollmentData>;
    } | null
  >();
  twoStep = computed(() => this.authService.check2Step("totp"));
  twoStepControl = new FormControl<boolean>(this.twoStep() === "force");
  generateOnServerFormControl = new FormControl<boolean>(true, [Validators.required]);
  otpLengthFormControl = new FormControl<number>(6, [Validators.required]);
  otpKeyFormControl = new FormControl<string>({ value: "", disabled: true });
  defaultHashlib = computed(() => this.systemService.systemConfig()[TOTP_HASHLIB] || "sha1");
  hashAlgorithmControl = new FormControl<string>(this.defaultHashlib(), [Validators.required]);
  defaultTimeStep = computed(() => {
    let timeStep = 30;
    const configTimeStep = this.systemService.systemConfig()[TOTP_TIME_STEP];
    if (configTimeStep) {
      const parsedTimeStep = parseInt(configTimeStep, 10);
      if (!isNaN(parsedTimeStep)) {
        timeStep = parsedTimeStep;
      }
    }
    return timeStep;
  });
  timeStepControl = new FormControl<number | string>(this.defaultTimeStep(), [Validators.required]);
  totpForm = new FormGroup({
    generateOnServer: this.generateOnServerFormControl,
    otpLength: this.otpLengthFormControl,
    otpKey: this.otpKeyFormControl,
    hashAlgorithm: this.hashAlgorithmControl,
    timeStep: this.timeStepControl,
    twoStep: this.twoStepControl
  });

  disabled = input<boolean>(false);

  constructor() {
    effect(() => (this.disabled() ? this.totpForm.disable({ emitEvent: false }) : this._enableFormControls()));
    effect(() => {
      if (this.enrollmentData()) {
        this._setInitialFormValues({ enrollmentData: this.enrollmentData(), eventEmit: false });
      }
    });
  }

  ngOnInit(): void {
    this._setInitialFormValues({ enrollmentData: this.enrollmentData() });
    this.additionalFormFieldsChange.emit({
      twoStep: this.twoStepControl,
      generateOnServer: this.generateOnServerFormControl,
      otpLength: this.otpLengthFormControl,
      otpKey: this.otpKeyFormControl,
      hashAlgorithm: this.hashAlgorithmControl,
      timeStep: this.timeStepControl
    });
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
    this._applyPolicies();
  }

  private _setInitialFormValues(args: { enrollmentData?: TotpEnrollmentData | null; eventEmit?: boolean }) {
    const { enrollmentData, eventEmit } = args;
    if (enrollmentData) {
      this.twoStepControl.setValue(enrollmentData.twoStepInit ?? this.twoStep() === "force", {
        emitEvent: eventEmit
      });
      if (enrollmentData.generateOnServer) {
        this.otpKeyFormControl.disable({ emitEvent: eventEmit });
        this.twoStepControl.disable({ emitEvent: eventEmit });
      } else {
        this.otpKeyFormControl.enable({ emitEvent: eventEmit });
        this.otpKeyFormControl.disable({ emitEvent: eventEmit });
      }
      this.generateOnServerFormControl.setValue(enrollmentData.generateOnServer ?? true, { emitEvent: eventEmit });
      this.otpLengthFormControl.setValue(enrollmentData.otpLength ?? 6, { emitEvent: eventEmit });
      this.otpKeyFormControl.setValue(enrollmentData.otpKey ?? "", { emitEvent: eventEmit });
      this.hashAlgorithmControl.setValue(enrollmentData.hashAlgorithm ?? this.defaultHashlib(), { emitEvent: eventEmit });
      this.timeStepControl.setValue(enrollmentData.timeStep ?? this.defaultTimeStep(), { emitEvent: eventEmit });
    }
  }

  private _applyPolicies() {
    if (this.twoStep() === "force") {
      this.twoStepControl.setValue(true, { emitEvent: false });
      this.twoStepControl.disable({ emitEvent: false });
      this.generateOnServerFormControl.disable({ emitEvent: false });
    } else if (this.twoStep() === "allow") {
      this.twoStepControl.valueChanges.subscribe((twoStepEnabled) => {
        if (twoStepEnabled) {
          this.generateOnServerFormControl.disable({ emitEvent: false });
          this.generateOnServerFormControl.setValue(true);
        } else if (!this.authService.checkForceServerGenerateOTPKey("totp")) {
          this.generateOnServerFormControl.enable({ emitEvent: false });
        }
      });
    }

    if (this.authService.checkForceServerGenerateOTPKey("totp")) {
      this.generateOnServerFormControl.disable({ emitEvent: false });
    } else {
      this.generateOnServerFormControl.valueChanges.subscribe(() => {
        this._enableDisableOtpKeyControl(false);
      });
    }

    const hashlib = this.authService.rightsWithValues()[TOTP_HASHLIB];
    if (hashlib) {
      this.hashAlgorithmControl.setValue(hashlib, { emitEvent: false });
      this.hashAlgorithmControl.disable({ emitEvent: false });
    }
    const otpLength = this.authService.rightsWithValues()[TOTP_OTP_LENGTH];
    if (otpLength) {
      const otpLengthNumber = parseInt(otpLength, 10);
      if (!isNaN(otpLengthNumber)) {
        this.otpLengthFormControl.setValue(otpLengthNumber, { emitEvent: false });
        this.otpLengthFormControl.disable({ emitEvent: false });
      }
    }
    const timeStep = this.authService.rightsWithValues()[TOTP_TIME_STEP];
    if (timeStep) {
      const timeStepNumber = parseInt(timeStep, 10);
      if (!isNaN(timeStepNumber)) {
        this.timeStepControl.setValue(timeStepNumber, { emitEvent: false });
        this.timeStepControl.disable({ emitEvent: false });
      }
    }
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: TotpEnrollmentData;
    mapper: TokenApiPayloadMapper<TotpEnrollmentData>;
  } | null => {
    const timeStepValue =
      typeof this.timeStepControl.value === "string"
        ? parseInt(this.timeStepControl.value, 10)
        : (this.timeStepControl.value ?? 30);

    const enrollmentData: TotpEnrollmentOptions = {
      ...basicOptions,
      type: "totp",
      generateOnServer: !!this.generateOnServerFormControl.value,
      otpLength: this.otpLengthFormControl.value ?? 6,
      hashAlgorithm: this.hashAlgorithmControl.value ?? "sha1",
      timeStep: timeStepValue,
      twoStepInit: !!this.twoStepControl.value
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value ?? "";
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  private _enableDisableOtpKeyControl(emitEvent: boolean = true): void {
    if (!this.generateOnServerFormControl.value) {
      this.otpKeyFormControl.enable({ emitEvent });
      this.otpKeyFormControl.setValidators([Validators.required, Validators.minLength(16)]);
    } else {
      this.otpKeyFormControl.disable({ emitEvent });
      this.otpKeyFormControl.clearValidators();
      this.otpKeyFormControl.setValue("");
    }
    this.otpKeyFormControl.updateValueAndValidity();
  }

  private _enableFormControls(): void {
    this.generateOnServerFormControl.enable();
    this.otpLengthFormControl.enable();
    this._enableDisableOtpKeyControl();
    this.hashAlgorithmControl.enable();
    this.timeStepControl.enable();
    this.twoStepControl.enable();
    this._applyPolicies();
  }
}
