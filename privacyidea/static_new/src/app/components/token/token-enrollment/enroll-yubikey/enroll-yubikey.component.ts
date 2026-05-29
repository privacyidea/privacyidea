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
import { Component, effect, forwardRef, inject, input, OnInit, signal } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { form, FormField, required, validate } from "@angular/forms/signals";

import { MatOptionModule } from "@angular/material/core";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  YubikeyApiPayloadMapper,
  YubikeyEnrollmentData
} from "@app/mappers/token-api-payload/yubikey-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-enroll-yubikey",
  templateUrl: "./enroll-yubikey.component.html",
  styleUrls: ["./enroll-yubikey.component.scss"],
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, MatOptionModule, FormField],
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollYubikeyComponent) }
  ]
})
export class EnrollYubikeyComponent extends EnrollTokenBase<YubikeyEnrollmentData> implements OnInit {
  protected readonly enrollmentMapper: YubikeyApiPayloadMapper = inject(YubikeyApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  enrollmentData = input<YubikeyEnrollmentData>();

  testYubiKey = signal<string>("");
  otpKey = signal<string>("");
  otpLength = signal<number>(44);

  otpKeyForm = form(this.otpKey, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value().length !== 32 ? [{ kind: "invalidLength" as any }] : []));
  });
  otpLengthForm = form(this.otpLength, (f) => {
    required(f);
    validate(f, (ctx) => (ctx.value() < 32 ? [{ kind: "min" as any }] : []));
  });

  constructor() {
    super();

    effect(() => {
      const len = Math.max(32, this.testYubiKey().length);
      if (this.otpLength() !== len) this.otpLength.set(len);
    });
  }

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<YubikeyEnrollmentData> | null {
    if (!this.otpKeyForm().valid() || !this.otpLengthForm().valid()) {
      this.otpKeyForm().markAsTouched();
      this.otpLengthForm().markAsTouched();
      return null;
    }

    const enrollmentData: YubikeyEnrollmentData = {
      ...basicOptions,
      type: "yubikey",
      otpKey: this.otpKey(),
      otpLength: this.otpLength()
    };

    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }

  ngOnInit(): void {
    if (this.enrollmentData()) {
      this.otpKey.set(this.enrollmentData()?.otpKey ?? "");
      this.otpLength.set(this.enrollmentData()?.otpLength ?? 44);
    }
  }
}
