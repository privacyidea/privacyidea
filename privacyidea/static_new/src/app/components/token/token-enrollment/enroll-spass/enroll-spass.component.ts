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
import { Component, EventEmitter, inject, Input, OnInit, Output } from "@angular/core";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";

import {
  SpassApiPayloadMapper,
  SpassEnrollmentData
} from "../../../../mappers/token-api-payload/spass-token-api-payload.mapper";
import {
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "../../../../mappers/token-api-payload/_token-api-payload.mapper";

export interface SpassEnrollmentOptions extends TokenEnrollmentData {
  type: "spass";
}

@Component({
  selector: "app-enroll-spass",
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule],
  templateUrl: "./enroll-spass.component.html",
  styleUrl: "./enroll-spass.component.scss"
})
export class EnrollSpassComponent implements OnInit {
  protected readonly enrollmentMapper: SpassApiPayloadMapper = inject(SpassApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  @Input() wizard: boolean = false;
  @Output() additionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() getEnrollmentDataChange = new EventEmitter<
    (basicOptions: TokenEnrollmentData) => {
      data: SpassEnrollmentData;
      mapper: TokenApiPayloadMapper<SpassEnrollmentData>;
    } | null
  >();

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({});
    this.getEnrollmentDataChange.emit(this.getEnrollmentData);
  }

  getEnrollmentData = (
    basicOptions: TokenEnrollmentData
  ): {
    data: SpassEnrollmentData;
    mapper: TokenApiPayloadMapper<SpassEnrollmentData>;
  } | null => {
    const enrollmentData: SpassEnrollmentOptions = {
      ...basicOptions,
      type: "spass"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  };
}
