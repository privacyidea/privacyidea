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
import { Component, inject, input, OnInit, signal, output } from '@angular/core';
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";

import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  IndexedSecretApiPayloadMapper,
  IndexedSecretEnrollmentData
} from "@app/mappers/token-api-payload/indexedsecret-token-api-payload.mapper";

export interface IndexedSecretEnrollmentOptions extends TokenEnrollmentData {
  type: "indexedsecret";
  otpKey: string;
}

@Component({
  selector: "app-enroll-indexedsecret",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, MatError, FormField],
  templateUrl: "./enroll-indexedsecret.component.html",
  styleUrl: "./enroll-indexedsecret.component.scss"
})
export class EnrollIndexedsecretComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper = inject(IndexedSecretApiPayloadMapper);

  disabled = input<boolean>(false);

  additionalFormFieldsChange = output<Record<string, unknown>>();
  enrollmentArgsGetterChange = output<(basicOptions: TokenEnrollmentData) => {
      data: IndexedSecretEnrollmentData;
      mapper: TokenApiPayloadMapper<IndexedSecretEnrollmentData>;
    } | null>();

  otpKey = signal<string>("");
  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length < 16 ? [{ kind: "minlength" }] : []));
    disabled(f, () => this.disabled());
  });

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: IndexedSecretEnrollmentData;
    mapper: TokenApiPayloadMapper<IndexedSecretEnrollmentData>;
  } | null => {
    if (!this.otpKeyForm().valid()) {
      this.otpKeyForm().markAsTouched();
      return null;
    }
    const enrollmentData: IndexedSecretEnrollmentOptions = {
      ...basicOptions,
      type: "indexedsecret",
      otpKey: this.otpKey()
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
