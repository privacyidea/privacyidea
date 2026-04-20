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
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatHint, MatLabel, MatError } from "@angular/material/form-field";
import { MatOption, MatSelect } from "@angular/material/select";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  HotpApiPayloadMapper,
  HotpEnrollmentData
} from "../../../../mappers/token-api-payload/hotp-token-api-payload.mapper";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../../../../services/notification/notification.service";
import { SystemService, SystemServiceInterface } from "../../../../services/system/system.service";
import { HOTP_HASHLIB, HOTP_OTP_LENGTH } from "../../../../constants/token.constants";

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
  imports: [
    MatCheckbox,
    FormsModule,
    MatSelect,
    MatOption,
    MatLabel,
    MatFormField,
    MatInput,
    MatHint,
    MatError,
    ReactiveFormsModule
  ],
  templateUrl: "./enroll-hotp.component.html",
  styleUrl: "./enroll-hotp.component.scss",
  standalone: true
})
export class EnrollHotpComponent implements OnInit {
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
  @Input() wizard: boolean = false;
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: HotpEnrollmentData;
      mapper: TokenApiPayloadMapper<HotpEnrollmentData>;
    } | null
  >();
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  disabled = input<boolean>(false);
  twoStep = computed(() => this.authService.check2Step("hotp"));
  twoStepControl = new FormControl<boolean>(this.twoStep() === "force");
  generateOnServerFormControl = new FormControl<boolean>(true, [Validators.required]);
  otpLengthFormControl = new FormControl<number>(6, [Validators.required]);
  otpKeyFormControl = new FormControl<string>({ value: "", disabled: true });
  defaultHashlib = computed(() => this.systemService.systemConfig()[HOTP_HASHLIB] || "sha1");
  hashAlgorithmFormControl = new FormControl<string>(this.defaultHashlib(), [Validators.required]);

  constructor() {
    effect(() => (this.disabled() ? this._disableFormControls() : this._enableFormControls()));
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
      hashAlgorithm: this.hashAlgorithmFormControl
    });
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
    this._applyPolicies();
  }

  private _setInitialFormValues(args: { enrollmentData?: HotpEnrollmentData | null; eventEmit?: boolean }): void {
    const { enrollmentData, eventEmit } = args;
    if (enrollmentData) {
      this.generateOnServerFormControl.setValue(enrollmentData.generateOnServer ?? true, {
        emitEvent: eventEmit
      });
      if (enrollmentData.generateOnServer) {
        this.otpKeyFormControl.disable({ emitEvent: eventEmit });
        this.twoStepControl.disable({ emitEvent: eventEmit });
      } else {
        this.otpKeyFormControl.enable({ emitEvent: eventEmit });
        this.otpKeyFormControl.disable({ emitEvent: eventEmit });
      }
      this.twoStepControl.setValue(enrollmentData.twoStepInit ?? false, { emitEvent: eventEmit });
      this.otpLengthFormControl.setValue(enrollmentData.otpLength ?? 6, { emitEvent: eventEmit });
      this.otpKeyFormControl.setValue(enrollmentData.otpKey ?? "", { emitEvent: eventEmit });
      this.hashAlgorithmFormControl.setValue(enrollmentData.hashAlgorithm ?? "sha1", { emitEvent: eventEmit });
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
        } else if (!this.authService.checkForceServerGenerateOTPKey("hotp")) {
          this.generateOnServerFormControl.enable({ emitEvent: false });
        }
      });
    }

    if (this.authService.checkForceServerGenerateOTPKey("hotp")) {
      this.generateOnServerFormControl.disable({ emitEvent: false });
    } else {
      this.generateOnServerFormControl.valueChanges.subscribe((generate) => {
        if (!generate) {
          this.otpKeyFormControl.enable({ emitEvent: false });
          this.otpKeyFormControl.setValidators([Validators.required]);
        } else {
          this.otpKeyFormControl.disable({ emitEvent: false });
          this.otpKeyFormControl.clearValidators();
          this.otpKeyFormControl.setValue("");
        }
        this.otpKeyFormControl.updateValueAndValidity();
      });
    }

    const hashlib = this.authService.rightsWithValues()[HOTP_HASHLIB];
    if (hashlib) {
      this.hashAlgorithmFormControl.setValue(hashlib, { emitEvent: false });
      this.hashAlgorithmFormControl.disable({ emitEvent: false });
    }
    const otpLength = this.authService.rightsWithValues()[HOTP_OTP_LENGTH];
    if (otpLength) {
      const otpLengthNumber = parseInt(otpLength, 10);
      if (!isNaN(otpLengthNumber)) {
        this.otpLengthFormControl.setValue(otpLengthNumber, { emitEvent: false });
        this.otpLengthFormControl.disable({ emitEvent: false });
      }
    }
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: HotpEnrollmentData;
    mapper: TokenApiPayloadMapper<HotpEnrollmentData>;
  } | null => {
    const enrollmentData: HotpEnrollmentOptions = {
      ...basicOptions,
      type: "hotp",
      generateOnServer: !!this.generateOnServerFormControl.value,
      otpLength: this.otpLengthFormControl.value ?? 6,
      hashAlgorithm: this.hashAlgorithmFormControl.value ?? "sha1",
      twoStepInit: !!this.twoStepControl.value
    };

    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value?.trim() ?? "";
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };

  private _disableFormControls(): void {
    this.generateOnServerFormControl.disable();
    this.otpLengthFormControl.disable();
    this.otpKeyFormControl.disable();
    this.hashAlgorithmFormControl.disable();
  }

  private _enableFormControls(): void {
    this.generateOnServerFormControl.enable();
    this.otpLengthFormControl.enable();
    if (!this.generateOnServerFormControl.value) {
      this.otpKeyFormControl.enable();
    }
    this.hashAlgorithmFormControl.enable();
    this._applyPolicies();
  }
}
