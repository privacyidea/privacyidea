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
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import {
  U2fApiPayloadMapper,
  U2fEnrollmentData
} from "../../../../mappers/token-api-payload/u2f-token-api-payload.mapper";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";

export interface U2fEnrollmentOptions extends TokenEnrollmentData {
  type: "u2f";
}

@Component({
  selector: "app-enroll-u2f",
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: "./enroll-u2f.component.html",
  styleUrl: "./enroll-u2f.component.scss"
})
export class EnrollU2fComponent implements OnInit {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: U2fApiPayloadMapper = inject(U2fApiPayloadMapper);

  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() enrollmentArgsGetterChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: U2fEnrollmentData;
      mapper: TokenApiPayloadMapper<U2fEnrollmentData>;
    } | null
  >();

  u2fForm = new FormGroup({});

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.enrollmentArgsGetterChange.emit(this.enrollmentArgsGetter);
  }

  enrollmentArgsGetter = (
    basicOptions: TokenEnrollmentData
  ): {
    data: U2fEnrollmentData;
    mapper: TokenApiPayloadMapper<U2fEnrollmentData>;
  } | null => {
    const enrollmentData: U2fEnrollmentOptions = {
      ...basicOptions,
      type: "u2f"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
