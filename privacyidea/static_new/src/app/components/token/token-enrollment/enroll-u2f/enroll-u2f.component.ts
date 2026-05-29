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
import { Component, forwardRef, inject } from "@angular/core";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { U2fApiPayloadMapper, U2fEnrollmentData } from "@app/mappers/token-api-payload/u2f-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";

export interface U2fEnrollmentOptions extends TokenEnrollmentData {
  type: "u2f";
}

@Component({
  selector: "app-enroll-u2f",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-u2f.component.html",
  styleUrl: "./enroll-u2f.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollU2fComponent) }
  ]
})
export class EnrollU2fComponent extends EnrollTokenBase<U2fEnrollmentData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: U2fApiPayloadMapper = inject(U2fApiPayloadMapper);

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<U2fEnrollmentData> | null {
    const enrollmentData: U2fEnrollmentOptions = {
      ...basicOptions,
      type: "u2f"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
