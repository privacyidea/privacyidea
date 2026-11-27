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
import { PushApiPayloadMapper, PushEnrollmentData } from "@app/mappers/token-api-payload/push-token-api-payload.mapper";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { EnrollmentArgs, EnrollTokenBase } from "@components/token/token-enrollment/enroll-token-base";
import type { EnrollmentFirstStep } from "@components/token/token-enrollment/enrollment-flow";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";

@Component({
  selector: "app-enroll-push",
  standalone: true,
  imports: [],
  templateUrl: "./enroll-push.component.html",
  providers: [{ provide: EnrollTokenBase, useExisting: forwardRef(() => EnrollPushComponent) }]
})
export class EnrollPushComponent extends EnrollTokenBase<PushEnrollmentData> {
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly enrollmentMapper: PushApiPayloadMapper = inject(PushApiPayloadMapper);

  text = this.tokenService.tokenTypeOptions().find((type) => type.key === "push")?.text;

  override readonly showEnrollDataInLastStep: boolean = false;

  buildEnrollmentArgs(basicOptions: TokenEnrollmentData): EnrollmentArgs<PushEnrollmentData> | null {
    const enrollmentData: PushEnrollmentData = {
      ...basicOptions,
      type: "push"
    };
    return {
      data: enrollmentData,
      mapper: this.enrollmentMapper
    };
  }

  override firstStep(): EnrollmentFirstStep {
    return { kind: "push" };
  }
}
