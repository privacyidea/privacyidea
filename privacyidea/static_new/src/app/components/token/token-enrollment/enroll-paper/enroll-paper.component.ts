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
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  PaperApiPayloadMapper,
  PaperEnrollmentData
} from "@app/mappers/token-api-payload/paper-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

export interface PaperEnrollmentOptions extends TokenEnrollmentData {
  type: "paper";
}

@Component({
  selector: "app-enroll-paper",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-paper.component.html",
  styleUrl: "./enroll-paper.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollPaperComponent) }
  ]
})
export class EnrollPaperComponent extends EnrollTokenBase<PaperEnrollmentData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: PaperApiPayloadMapper = inject(PaperApiPayloadMapper);

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<PaperEnrollmentData> | null {
    const enrollmentData: PaperEnrollmentOptions = {
      ...basicOptions,
      type: "paper"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
