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
import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatOption } from "@angular/material/core";
import { MatError, MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { DaypasswordApiPayloadMapper } from "../../../../mappers/token-api-payload/daypassword-token-api-payload.mapper";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

export interface DaypasswordEnrollmentOptions extends TokenEnrollmentData {
  type: "daypassword";
  otpKey?: string;
  otpLength: number;
  hashAlgorithm: string;
  timeStep: number;
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
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: DaypasswordApiPayloadMapper = inject(DaypasswordApiPayloadMapper);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  readonly otpLengthOptions = [6, 8];
  readonly hashAlgorithmOptions = [
    { value: "sha1", viewValue: "SHA1" },
    { value: "sha256", viewValue: "SHA256" },
    { value: "sha512", viewValue: "SHA512" }
  ];
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  otpKeyFormControl = new FormControl<string>({ value: "", disabled: true });
  hashAlgorithmControl = new FormControl<string>("sha256", [Validators.required]);
  timeStepControl = new FormControl<number | string>(86400, [Validators.required]);
  generateOnServerControl = new FormControl(true);
  otpLengthControl = new FormControl<number>(6, [Validators.required]);

  daypasswordForm = new FormGroup({
    otpKey: this.otpKeyFormControl,
    otpLength: this.otpLengthControl,
    hashAlgorithm: this.hashAlgorithmControl,
    timeStep: this.timeStepControl
  });

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      otpKey: this.otpKeyFormControl,
      otpLength: this.otpLengthControl,
      hashAlgorithm: this.hashAlgorithmControl,
      timeStep: this.timeStepControl,
      generateOnServer: this.generateOnServerControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.updateOtpKeyControlState(this.generateOnServerControl.value ?? true);

    if (this.authService.checkForceServerGenerateOTPKey("daypassword")) {
      this.generateOnServerControl.disable({ emitEvent: false });
    } else {
      this.generateOnServerControl.valueChanges.subscribe((generateOnServer) => {
        this.updateOtpKeyControlState(generateOnServer ?? true);
      });
    }
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (this.daypasswordForm.invalid) {
      this.daypasswordForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: DaypasswordEnrollmentOptions = {
      ...basicOptions,
      type: "daypassword",
      otpLength: this.otpLengthControl.value ?? 10,
      hashAlgorithm: this.hashAlgorithmControl.value ?? "sha256",
      timeStep:
        typeof this.timeStepControl.value === "string"
          ? parseInt(this.timeStepControl.value, 10)
          : (this.timeStepControl.value ?? 86400),
      generateOnServer: (this.generateOnServerControl.value ?? true)
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKeyFormControl.value ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
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
}
