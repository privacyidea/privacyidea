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
  DaypasswordApiPayloadMapper,
  DaypasswordEnrollmentData
} from "../../../../mappers/token-api-payload/daypassword-token-api-payload.mapper";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import { TokenEnrollmentData } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import {
  DAYPASSWORD_HASHLIB,
  DAYPASSWORD_OTP_LENGTH,
  DAYPASSWORD_TIME_STEP
} from "../../../../constants/token.constants";

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
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    MatError,
    MatCheckbox
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
  @Input() wizard: boolean = false;
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: DaypasswordEnrollmentData;
      mapper: DaypasswordApiPayloadMapper;
    } | null
  >();
  disabled = input<boolean>(false);

  otpKeyFormControl = new FormControl<string>({ value: "", disabled: true });
  defaultHashlib = computed(() => this.systemService.systemConfig()[DAYPASSWORD_HASHLIB] || "sha1");
  hashAlgorithmControl = new FormControl<string>(this.defaultHashlib(), [Validators.required]);
  defaultTimeStep = computed(() => this.systemService.systemConfig()[DAYPASSWORD_TIME_STEP] || "24h");
  timeStepControl = new FormControl<string>(this.defaultTimeStep(), [Validators.required]);
  generateOnServerControl = new FormControl(true);
  otpLengthControl = new FormControl<number>(6, [Validators.required]);

  daypasswordForm = new FormGroup({
    otpKey: this.otpKeyFormControl,
    otpLength: this.otpLengthControl,
    hashAlgorithm: this.hashAlgorithmControl,
    timeStep: this.timeStepControl
  });

  constructor() {
    effect(() => (this.disabled() ? this.daypasswordForm.disable({ emitEvent: false }) : this._enableFormControls()));
  }

  ngOnInit(): void {
    this._setInitialFormValues();
    this.additionalFormFieldsChange.emit({
      otpKey: this.otpKeyFormControl,
      otpLength: this.otpLengthControl,
      hashAlgorithm: this.hashAlgorithmControl,
      timeStep: this.timeStepControl,
      generateOnServer: this.generateOnServerControl
    });
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
    this._applyPolicies();
  }

  private _setInitialFormValues() {
    if (!!this.enrollmentData()) {
      this.otpKeyFormControl.setValue(this.enrollmentData()?.otpKey ?? "", { emitEvent: false });
      this.otpLengthControl.setValue(this.enrollmentData()?.otpLength ?? 6, { emitEvent: false });
      this.hashAlgorithmControl.setValue(this.enrollmentData()?.hashAlgorithm ?? "sha256", { emitEvent: false });
      this.timeStepControl.setValue(this.enrollmentData()?.timeStep ?? "24h", { emitEvent: false });
      this.generateOnServerControl.setValue(this.enrollmentData()?.generateOnServer ?? true, { emitEvent: false });
    }
  }

  private _applyPolicies() {
    this.updateOtpKeyControlState(this.generateOnServerControl.value ?? true);

    if (this.authService.checkForceServerGenerateOTPKey("daypassword")) {
      this.generateOnServerControl.disable({ emitEvent: false });
    } else {
      this.generateOnServerControl.valueChanges.subscribe((generateOnServer) => {
        this.updateOtpKeyControlState(generateOnServer ?? true);
      });
    }

    const hashlib = this.authService.rightsWithValues()[DAYPASSWORD_HASHLIB];
    if (hashlib) {
      this.hashAlgorithmControl.setValue(hashlib, { emitEvent: false });
      this.hashAlgorithmControl.disable({ emitEvent: false });
    }
    const otpLength = this.authService.rightsWithValues()[DAYPASSWORD_OTP_LENGTH];
    if (otpLength) {
      const otpLengthNumber = parseInt(otpLength, 10);
      if (!isNaN(otpLengthNumber)) {
        this.otpLengthControl.setValue(otpLengthNumber, { emitEvent: false });
        this.otpLengthControl.disable({ emitEvent: false });
      }
    }
    const timeStep = this.authService.rightsWithValues()[DAYPASSWORD_TIME_STEP];
    if (timeStep) {
      this.timeStepControl.setValue(timeStep, { emitEvent: false });
      this.timeStepControl.disable({ emitEvent: false });
    }
  }

  enrollmentArgsGetter = (basicOptions: TokenEnrollmentData): {
    data: DaypasswordEnrollmentData;
    mapper: DaypasswordApiPayloadMapper;
  } | null => {
    if (this.daypasswordForm.invalid) {
      this.daypasswordForm.markAllAsTouched();
      this.notificationService.openSnackBar($localize`Invalid enrollment data.`);
      return null;
    }
    const enrollmentData: DaypasswordEnrollmentOptions = {
      ...basicOptions,
      type: "daypassword",
      otpLength: this.otpLengthControl.value ?? 10,
      hashAlgorithm: this.hashAlgorithmControl.value ?? "sha256",
      timeStep: this.timeStepControl.value ?? "24h",
      generateOnServer: this.generateOnServerControl.value ?? true
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value ?? "";
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  private updateOtpKeyControlState(generateOnServer: boolean): void {
    if (generateOnServer) {
      this.otpKeyFormControl.disable({ emitEvent: false });
      this.otpKeyFormControl.clearValidators();
    } else {
      this.otpKeyFormControl.enable({ emitEvent: false });
      this.otpKeyFormControl.setValidators([Validators.required, Validators.minLength(16)]);
    }
    this.otpKeyFormControl.updateValueAndValidity();
  }

  private _enableFormControls(): void {
    this.daypasswordForm.enable({ emitEvent: false });
    this._applyPolicies();
  }
}
