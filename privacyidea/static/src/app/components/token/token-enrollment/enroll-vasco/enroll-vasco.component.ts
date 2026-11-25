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
import { Component, computed, forwardRef, inject, input, signal } from "@angular/core";
import { disabled, form, FormField, pattern, required } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  VascoApiPayloadMapper,
  VascoEnrollmentData
} from "@app/mappers/token-api-payload/vasco-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";

// A VASCO token blob: 248 bytes as hex.
const BLOB_PATTERN = /^[0-9a-fA-F]{496}$/;

// The VASCO serial: the first ten bytes of the blob.
function vascoSerialFromBlob(blob: string): string {
  let serial = "";
  for (let i = 0; i < 20; i += 2) {
    serial += String.fromCharCode(parseInt(blob.slice(i, i + 2), 16));
  }
  return serial;
}

export interface VascoEnrollmentOptions extends TokenEnrollmentData {
  type: "vasco";
  otpKey: string;
  useVascoSerial: boolean;
  vascoSerial?: string;
}

@Component({
  selector: "app-enroll-vasco",
  standalone: true,
  imports: [FormField, MatFormField, MatInput, MatLabel, MatCheckbox, MatError],
  templateUrl: "./enroll-vasco.component.html",
  styleUrl: "./enroll-vasco.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollVascoComponent) }
  ]
})
export class EnrollVascoComponent extends EnrollTokenBase<VascoEnrollmentData> {
  protected readonly enrollmentMapper: VascoApiPayloadMapper = inject(VascoApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;
  disabled = input<boolean>(false);

  useVascoSerial = signal<boolean>(false);
  otpKey = signal<string>("");
  // The serial is the start of the blob; the checkbox only decides whether the token gets it.
  vascoSerial = computed(() => (BLOB_PATTERN.test(this.otpKey()) ? vascoSerialFromBlob(this.otpKey()) : ""));

  useVascoSerialForm = form(this.useVascoSerial);

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    pattern(f, BLOB_PATTERN);
    disabled(f, () => this.disabled());
  });

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<VascoEnrollmentData> | null {
    if (!this.otpKeyForm().valid()) {
      this.otpKeyForm().markAsTouched();
      return null;
    }

    const enrollmentData: VascoEnrollmentOptions = {
      ...basicOptions,
      type: "vasco",
      otpKey: this.otpKey(),
      useVascoSerial: this.useVascoSerial()
    };
    if (enrollmentData.useVascoSerial) {
      enrollmentData.vascoSerial = this.vascoSerial();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
