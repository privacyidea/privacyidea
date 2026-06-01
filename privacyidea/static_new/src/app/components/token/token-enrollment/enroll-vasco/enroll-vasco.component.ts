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
import { Component, inject, input, OnInit, signal, output } from "@angular/core";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  VascoApiPayloadMapper,
  VascoEnrollmentData
} from "@app/mappers/token-api-payload/vasco-token-api-payload.mapper";

export interface VascoEnrollmentOptions extends TokenEnrollmentData {
  type: "vasco";
  otpKey?: string;
  useVascoSerial: boolean;
  vascoSerial?: string;
}

@Component({
  selector: "app-enroll-vasco",
  standalone: true,
  imports: [FormField, MatFormField, MatInput, MatLabel, MatCheckbox, MatError],
  templateUrl: "./enroll-vasco.component.html",
  styleUrl: "./enroll-vasco.component.scss"
})
export class EnrollVascoComponent implements OnInit {
  protected readonly enrollmentMapper = inject(VascoApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  disabled = input<boolean>(false);

  additionalFormFieldsChange = output<Record<string, unknown>>();
  enrollmentArgsGetterChange = output<
    (basicOptions: TokenEnrollmentData) => {
      data: VascoEnrollmentData;
      mapper: TokenApiPayloadMapper<VascoEnrollmentData>;
    } | null
  >();

  useVascoSerial = signal<boolean>(false);
  otpKey = signal<string>("");
  vascoSerial = signal<string>("");

  otpKeyForm = form(this.otpKey, (f) => {
    validate(f, (ctx) => (ctx.value().length !== 496 ? [{ kind: "invalidLength" }] : []));
    disabled(f, () => this.disabled() || this.useVascoSerial());
  });

  vascoSerialForm = form(this.vascoSerial, (f) => {
    required(f);
    disabled(f, () => this.disabled() || !this.useVascoSerial());
  });

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
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: VascoEnrollmentData;
    mapper: TokenApiPayloadMapper<VascoEnrollmentData>;
  } | null => {
    if (!this.useVascoSerial() && !this.otpKeyForm().valid()) {
      this.otpKeyForm().markAsTouched();
      return null;
    }
    if (this.useVascoSerial() && !this.vascoSerialForm().valid()) {
      this.vascoSerialForm().markAsTouched();
      return null;
    }

    const enrollmentData: VascoEnrollmentOptions = {
      ...basicOptions,
      type: "vasco",
      useVascoSerial: this.useVascoSerial()
    };

    if (enrollmentData.useVascoSerial) {
      enrollmentData.vascoSerial = this.vascoSerial();
    } else {
      enrollmentData.otpKey = this.otpKey();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
