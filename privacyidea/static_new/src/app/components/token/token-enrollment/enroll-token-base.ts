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

import { signal, WritableSignal } from "@angular/core";
import {
  EnrollmentResponse,
  TokenApiPayloadMapper,
  TokenEnrollmentData
} from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { Observable } from "rxjs";

export interface EnrollmentArgs<T extends TokenEnrollmentData> {
  data: T;
  mapper: TokenApiPayloadMapper<T>;
}

export type ReopenDialogAction = () => Promise<EnrollmentResponse | null> | Observable<EnrollmentResponse | null>;

// Abstract class so it can be used as a DI token via
// `{ provide: EnrollTokenBase, useExisting: forwardRef(() => MyEnrollComponent) }`.
// The parent then resolves the active child with `viewChild(EnrollTokenBase)` instead of having children emit a
// function reference via @Output.
export abstract class EnrollTokenBase<T extends TokenEnrollmentData = TokenEnrollmentData> {
  abstract buildEnrollmentArgs(basic: TokenEnrollmentData): EnrollmentArgs<T> | null;

  onEnrollmentResponse?(response: EnrollmentResponse, data: TokenEnrollmentData): Promise<EnrollmentResponse | null>;

  readonly showEnrollDataInLastStep: boolean = true;

  readonly reopenDialog: WritableSignal<ReopenDialogAction | undefined> = signal<ReopenDialogAction | undefined>(
    undefined
  );
}
