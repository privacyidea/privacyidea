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
import { computed, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  BlocklistEntry,
  ConditionalAccessStateServiceInterface,
  LockedUsersPage,
  LockedUserEntry,
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

  lockedUsersFilter = signal(new FilterValue());
  lockedUsersFilterParams = computed<Record<string, string>>(() => ({}));
  lockedUsersSort = signal<Sort>({ active: "last_updated", direction: "desc" });
  lockedUsersPageSize = signal(15);
  lockedUsersPageIndex = signal(1);

  lockedUsersResource = new MockHttpResourceRef<PiResponse<LockedUsersPage> | undefined>(
    MockPiResponse.fromValue<LockedUsersPage>({ locked_users: [], count: 0, current: 1, prev: null, next: null })
  );

  purgeUserLockouts = jest.fn().mockImplementation((): Observable<number> => of(0));

  // Blocklist — flat list
  blocklistResource = new MockHttpResourceRef<PiResponse<BlocklistEntry[]> | undefined>(
    MockPiResponse.fromValue<BlocklistEntry[]>([])
  );

  removeBlocklistEntry = jest.fn().mockImplementation((_: BlocklistEntry): Observable<boolean> => of(true));
  purgeBlocklist = jest.fn().mockImplementation((): Observable<number> => of(0));

  setUserLockoutStatus(value: UserLockoutStatus | null): void {
    this.userLockoutResource.set(MockPiResponse.fromValue<UserLockoutStatus | null>(value));
  }

  setUserLockoutResourceUndefined(): void {
    this.userLockoutResource.set(undefined);
  }

  setLockedUsers(entries: LockedUserEntry[]): void {
    this.lockedUsersResource.set(
      MockPiResponse.fromValue<LockedUsersPage>({
        locked_users: entries,
        count: entries.length,
        current: 1,
        prev: null,
        next: null
      })
    );
  }

  setLockedUsersResourceUndefined(): void {
    this.lockedUsersResource.set(undefined);
  }

  setBlocklistEntries(entries: BlocklistEntry[]): void {
    this.blocklistResource.set(MockPiResponse.fromValue<BlocklistEntry[]>(entries));
  }

  setBlocklistResourceUndefined(): void {
    this.blocklistResource.set(undefined);
  }
}
