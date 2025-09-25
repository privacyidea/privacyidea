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
import { CommonModule } from "@angular/common";
import { Component, EventEmitter, inject, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";

import { MatOptionModule } from "@angular/material/core";
import { distinctUntilChanged, map, Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import {
  YubikeyApiPayloadMapper,
  YubikeyEnrollmentData
} from "../../../../mappers/token-api-payload/yubikey-token-api-payload.mapper";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

@Component({
  selector: "app-enroll-yubikey",
  templateUrl: "./enroll-yubikey.component.html",
  styleUrls: ["./enroll-yubikey.component.scss"],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatOptionModule]
})
export class EnrollYubikeyComponent implements OnInit {
  protected readonly enrollmentMapper: YubikeyApiPayloadMapper = inject(YubikeyApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  testYubiKeyControl = new FormControl("");
  otpKeyControl = new FormControl("", [Validators.required, Validators.minLength(32), Validators.maxLength(32)]);
  otpLengthControl = new FormControl<number | null>(44, [Validators.required, Validators.min(32)]);

  yubikeyForm = new FormGroup({
    otpKey: this.otpKeyControl,
    otpLength: this.otpLengthControl
  });
  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    this.yubikeyForm.updateValueAndValidity();
    if (this.yubikeyForm.invalid) {
      this.yubikeyForm.markAllAsTouched();
      return of(null);
    }

    const enrollmentData: YubikeyEnrollmentData = {
      ...basicOptions,
      type: "yubikey",
      otpKey: this.otpKeyControl.value,
      otpLength: this.otpLengthControl.value
    };

    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl,
      otpLength: this.otpLengthControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);

    this.testYubiKeyControl.valueChanges
      .pipe(map(v => Math.max(32, (v ?? "").length)), distinctUntilChanged())
      .subscribe(len => {
        if (this.otpLengthControl.value !== len) {
          this.otpLengthControl.setValue(len, { emitEvent: false });
        }
      });
  }
}
