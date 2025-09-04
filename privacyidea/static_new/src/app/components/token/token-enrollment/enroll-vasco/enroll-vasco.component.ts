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
import { ErrorStateMatcher } from "@angular/material/core";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { VascoApiPayloadMapper } from "../../../../mappers/token-api-payload/vasco-token-api-payload.mapper";

export interface VascoEnrollmentOptions extends TokenEnrollmentData {
  type: "vasco";
  otpKey?: string;
  useVascoSerial: boolean;
  vascoSerial?: string;
}

export class VascoErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    const invalid = control && control.value ? control.value.length !== 496 : true;
    return !!(control && invalid && (control.dirty || control.touched));
  }
}

@Component({
  selector: "app-enroll-vasco",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule, MatCheckbox, MatError],
  templateUrl: "./enroll-vasco.component.html",
  styleUrl: "./enroll-vasco.component.scss"
})
export class EnrollVascoComponent implements OnInit {
  protected readonly enrollmentMapper: VascoApiPayloadMapper = inject(VascoApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  otpKeyControl = new FormControl<string>("");
  useVascoSerialControl = new FormControl<boolean>(false, [Validators.required]);
  vascoSerialControl = new FormControl<string>("");

  vascoForm = new FormGroup({
    otpKey: this.otpKeyControl,
    useVascoSerial: this.useVascoSerialControl,
    vascoSerial: this.vascoSerialControl
  });

  vascoErrorStatematcher = new VascoErrorStateMatcher();

  static convertOtpKeyToVascoSerial(otpHex: string): string {
    let vascoOtpStr = "";
    if (!otpHex || otpHex.length !== 496) {
      return "";
    }
    for (let i = 0; i < otpHex.length; i += 2) {
      vascoOtpStr += String.fromCharCode(parseInt(otpHex.slice(i, i + 2), 16));
    }
    return vascoOtpStr.slice(0, 10);
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl,
      useVascoSerial: this.useVascoSerialControl,
      vascoSerial: this.vascoSerialControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.useVascoSerialControl.valueChanges.subscribe((useSerial) => {
      if (useSerial) {
        this.vascoSerialControl.setValidators([Validators.required]);
        this.otpKeyControl.clearValidators();
      } else {
        this.otpKeyControl.setValidators([Validators.required, Validators.minLength(496), Validators.maxLength(496)]);
        this.vascoSerialControl.clearValidators();
      }
      this.otpKeyControl.updateValueAndValidity();
      this.vascoSerialControl.updateValueAndValidity();
    });
    this.useVascoSerialControl.updateValueAndValidity();
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (this.vascoForm.invalid) {
      this.vascoForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: VascoEnrollmentOptions = {
      ...basicOptions,
      type: "vasco",
      useVascoSerial: !!this.useVascoSerialControl.value
    };

    if (enrollmentData.useVascoSerial) {
      enrollmentData.vascoSerial = this.vascoSerialControl.value ?? "";
    } else {
      enrollmentData.otpKey = this.otpKeyControl.value ?? "";
    }
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
