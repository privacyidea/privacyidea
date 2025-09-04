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
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import { Observable, of } from "rxjs";
import {
  EnrollmentResponse,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { IndexedSecretApiPayloadMapper } from "../../../../mappers/token-api-payload/indexedsecret-token-api-payload.mapper";

export interface IndexedSecretEnrollmentOptions extends TokenEnrollmentData {
  type: "indexedsecret";
  otpKey: string;
}

@Component({
  selector: "app-enroll-indexedsecret",
  standalone: true,
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule, MatError],
  templateUrl: "./enroll-indexedsecret.component.html",
  styleUrl: "./enroll-indexedsecret.component.scss"
})
export class EnrollIndexedsecretComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: IndexedSecretApiPayloadMapper = inject(IndexedSecretApiPayloadMapper);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => Observable<EnrollmentResponse | null>
  >();

  otpKeyControl = new FormControl<string>("", [Validators.required, Validators.minLength(16)]);

  indexedSecretForm = new FormGroup({
    otpKey: this.otpKeyControl
  });

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      otpKey: this.otpKeyControl
    });
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (basicOptions: TokenEnrollmentData): Observable<EnrollmentResponse | null> => {
    if (this.otpKeyControl.invalid) {
      this.indexedSecretForm.markAllAsTouched();
      return of(null);
    }
    const enrollmentData: IndexedSecretEnrollmentOptions = {
      ...basicOptions,
      type: "indexedsecret",
      otpKey: this.otpKeyControl.value ?? ""
    };
    return this.tokenService.enrollToken({
      data: enrollmentData,
      mapper: this.enrollmentMapper
    });
  };
}
