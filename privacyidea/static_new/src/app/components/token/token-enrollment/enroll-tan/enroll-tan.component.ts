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
import { TanApiPayloadMapper, TanEnrollmentData } from "@app/mappers/token-api-payload/tan-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";

export interface TanEnrollmentOptions extends TokenEnrollmentData {
  type: "tan";
}

@Component({
  selector: "app-enroll-tan",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-tan.component.html",
  styleUrl: "./enroll-tan.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollTanComponent) }
  ]
})
export class EnrollTanComponent extends EnrollTokenBase<TanEnrollmentData> {
  protected readonly enrollmentMapper: TanApiPayloadMapper = inject(TanApiPayloadMapper);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<TanEnrollmentData> | null {
    const enrollmentData: TanEnrollmentOptions = {
      ...basicOptions,
      type: "tan"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
