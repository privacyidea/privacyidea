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
import { Component, computed, forwardRef, inject, input } from "@angular/core";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { TiqrApiPayloadMapper, TiqrEnrollmentData } from "@app/mappers/token-api-payload/tiqr-token-api-payload.mapper";
import {
  EnrollmentArgs,
  EnrollTokenBase
} from "@components/token/token-enrollment/enroll-token-base";
import { TIQR_INFO_URL, TIQR_LOGO_URL, TIQR_REG_SERVER } from "@constants/token.constants";

export interface TiqrEnrollmentOptions extends TokenEnrollmentData {
  type: "tiqr";
}

@Component({
  selector: "app-enroll-tiqr",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-tiqr.component.html",
  styleUrl: "./enroll-tiqr.component.scss",
  providers: [
    { provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollTiqrComponent) }
  ]
})
export class EnrollTiqrComponent extends EnrollTokenBase<TiqrEnrollmentData> {
  protected readonly enrollmentMapper: TiqrApiPayloadMapper = inject(TiqrApiPayloadMapper);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);

  wizard = input<boolean>(false);

  disabled = input<boolean>(false);
  defaultTiQRIsSet = computed(() => {
    if (!this.systemService.systemConfigResource.hasValue()) return false;
    const cfg = this.systemService.systemConfigResource.value()?.result?.value;
    return !!(cfg?.[TIQR_INFO_URL] && cfg?.[TIQR_LOGO_URL] && cfg?.[TIQR_REG_SERVER]);
  });

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<TiqrEnrollmentData> | null {
    const enrollmentData: TiqrEnrollmentOptions = {
      ...basicOptions,
      type: "tiqr"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }
}
