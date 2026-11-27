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

import { Signal, signal } from "@angular/core";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import type { EnrollmentFirstStep } from "@components/token/token-enrollment/enrollment-flow";

export interface EnrollmentArgs<T extends TokenEnrollmentData> {
  data: T;
  mapper: TokenApiPayloadMapper<T>;
}

// Abstract class so it can be used as a DI token via
// `{ provide: EnrollTokenBase, useExisting: forwardRef(() => MyEnrollComponent) }`.
// The parent then resolves the active child with `viewChild(EnrollTokenBase)` instead of having children emit a
// function reference via @Output.
export abstract class EnrollTokenBase<T extends TokenEnrollmentData = TokenEnrollmentData> {
  abstract buildEnrollmentArgs(basic: TokenEnrollmentData): EnrollmentArgs<T> | null;

  // The step this token type needs right after its first response, see push, WebAuthn and passkey.
  firstStep?(response: EnrollmentResponse, data: TokenEnrollmentData): EnrollmentFirstStep;

  readonly showEnrollDataInLastStep: boolean = true;

  // Set while the token type cannot be enrolled at all with the admin's rights; the parent disables Enroll and shows
  // the reason on it.
  readonly enrollmentBlockedReason: Signal<string | null> = signal(null);
}
