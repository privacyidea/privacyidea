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
import { computed } from "@angular/core";
import { PiResponse } from "@app/app.component";
import {
  ConditionalAccessStateServiceInterface,
  ResetUserLockoutRequest,
  UserLockoutStatus
} from "@services/conditional-access-state/conditional-access-state.service";
import { Observable, of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockConditionalAccessStateService implements ConditionalAccessStateServiceInterface {
  userLockoutResource = new MockHttpResourceRef<PiResponse<UserLockoutStatus | null> | undefined>(
    MockPiResponse.fromValue<UserLockoutStatus | null>(null)
  );

  userLockoutStatus = computed<UserLockoutStatus | null>(() => {
    if (!this.userLockoutResource.hasValue()) {
      return null;
    }
    return this.userLockoutResource.value()?.result?.value ?? null;
  });

  resetUserLockout = jest.fn().mockImplementation((_: ResetUserLockoutRequest): Observable<boolean> => of(true));

  setUserLockoutStatus(value: UserLockoutStatus | null): void {
    this.userLockoutResource.set(MockPiResponse.fromValue<UserLockoutStatus | null>(value));
  }

  setUserLockoutResourceUndefined(): void {
    this.userLockoutResource.set(undefined);
  }
}
