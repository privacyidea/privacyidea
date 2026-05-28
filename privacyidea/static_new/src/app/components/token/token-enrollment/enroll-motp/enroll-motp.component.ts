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
import { Component, inject, input, OnInit, output, signal } from '@angular/core';
import { disabled, form, FormField, required, validate } from "@angular/forms/signals";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenApiPayloadMapper, TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { MotpApiPayloadMapper, MotpEnrollmentData } from "@app/mappers/token-api-payload/motp-token-api-payload.mapper";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";

export interface MotpEnrollmentOptions extends TokenEnrollmentData {
  type: "motp";
  generateOnServer: boolean;
  otpKey?: string;
  motpPin: string;
}

@Component({
  selector: "app-enroll-motp",
  standalone: true,
  imports: [FormField, MatFormField, MatInput, MatLabel, MatCheckbox, MatError],
  templateUrl: "./enroll-motp.component.html",
  styleUrl: "./enroll-motp.component.scss"
})
export class EnrollMotpComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: MotpApiPayloadMapper = inject(MotpApiPayloadMapper);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  wizard = input(false);
  additionalFormFieldsChange = output<Record<string, unknown>>();
  enrollmentArgsGetterChange = output<(basicOptions: TokenEnrollmentData) => {
      data: MotpEnrollmentData;
      mapper: TokenApiPayloadMapper<MotpEnrollmentData>;
    } | null>();

  disabled = input<boolean>(false);

  generateOnServer = signal<boolean>(true);
  otpKey = signal<string>("");
  motpPin = signal<string>("");
  repeatMotpPin = signal<string>("");

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    disabled(f, () => this.disabled() || this.generateOnServer() || this.authService.checkForceServerGenerateOTPKey("motp"));
  });

  motpPinForm = form(this.motpPin, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length < 4 ? [{ kind: "minlength" }] : []));
    disabled(f, () => this.disabled());
  });

  repeatMotpPinForm = form(this.repeatMotpPin, (f) => {
    validate(f, (ctx) => (ctx.value() !== this.motpPin() ? [{ kind: "motpPinMismatch" }] : []));
    disabled(f, () => this.disabled());
  });

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: MotpEnrollmentData;
    mapper: TokenApiPayloadMapper<MotpEnrollmentData>;
  } | null => {
    if (!this.motpPinForm().valid()) {
      this.motpPinForm().markAsTouched();
      return null;
    }
    if (!this.repeatMotpPinForm().valid()) {
      this.repeatMotpPinForm().markAsTouched();
      return null;
    }
    if (!this.generateOnServer() && !this.otpKeyForm().valid()) {
      this.otpKeyForm().markAsTouched();
      return null;
    }

    const enrollmentData: MotpEnrollmentOptions = {
      ...basicOptions,
      type: "motp",
      generateOnServer: this.generateOnServer(),
      motpPin: this.motpPin()
    };
    if (!enrollmentData.generateOnServer) {
      enrollmentData.otpKey = this.otpKey();
    }
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
