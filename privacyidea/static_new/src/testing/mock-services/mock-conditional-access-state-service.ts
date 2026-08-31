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
  BlockIpRequest,
  BlocklistEntry,
  ConditionalAccessStateServiceInterface,
  LockedUsersPage,
  LockedUserEntry,
  LockState,
  ResetUserLockRequest,
  SetUserLockRequest
} from "@services/conditional-access-state/conditional-access-state.service";
import { Observable, of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockConditionalAccessStateService implements ConditionalAccessStateServiceInterface {
  userLockResource = new MockHttpResourceRef<PiResponse<LockedUserEntry | null> | undefined>(
    MockPiResponse.fromValue<LockedUserEntry | null>(null)
  );

  userLockStatus = computed<LockedUserEntry | null>(() => {
    if (!this.userLockResource.hasValue()) {
      return null;
    }
    return this.userLockResource.value()?.result?.value ?? null;
  });

  resetUserLock = jest.fn().mockImplementation((_: ResetUserLockRequest): Observable<boolean> => of(true));

  // Returns the lock the request asked for, so a caller that reads the result back gets a coherent entry.
  setUserLock = jest.fn().mockImplementation(
    (request: SetUserLockRequest): Observable<LockedUserEntry | null> =>
      of({
        resolver: request.resolver ?? "",
        uid: request.uid ?? "",
        realm: request.realm,
        username: request.login ?? "",
        permanent: request.duration_seconds == null,
        lock_expires_at: null,
        seconds_remaining: request.duration_seconds ?? null,
        lock_cause: "MANUAL",
        locked_at: ""
      })
  );

  lockedUsersFilter = signal(new FilterValue());
  lockedUsersFilterParams = computed<Record<string, string>>(() => ({}));
  lockedUsersSort = signal<Sort>({ active: "locked_at", direction: "desc" });
  lockedUsersPageSize = signal(15);
  lockedUsersPageIndex = signal(1);

  lockedUsersResource = new MockHttpResourceRef<PiResponse<LockedUsersPage> | undefined>(
    MockPiResponse.fromValue<LockedUsersPage>({ locked_users: [], count: 0, current: 1, prev: null, next: null })
  );

  // Counts per lock state, keyed by the states the caller asks for (see setLockedUsersCount).
  lockedUsersCounts = new Map<string, number>();

  countLockedUsers = jest.fn().mockImplementation(
    (states: LockState[]): Observable<PiResponse<LockedUsersPage>> =>
      of(
        MockPiResponse.fromValue<LockedUsersPage>({
          locked_users: [],
          count: this.lockedUsersCounts.get(states.join(",")) ?? 0,
          current: 1,
          prev: null,
          next: null
        })
      )
  );

  fetchLockedUsers = jest.fn().mockImplementation(
    (_states: LockState[], __ = 20): Observable<PiResponse<LockedUsersPage>> =>
      of(
        MockPiResponse.fromValue<LockedUsersPage>(
          this.lockedUsersResource.value()?.result?.value ?? {
            locked_users: [],
            count: 0,
            current: 1,
            prev: null,
            next: null
          }
        )
      )
  );

  purgeUserLocks = jest.fn().mockImplementation((): Observable<number> => of(0));

  // Blocklist — flat list
  blocklistResource = new MockHttpResourceRef<PiResponse<BlocklistEntry[]> | undefined>(
    MockPiResponse.fromValue<BlocklistEntry[]>([])
  );

  fetchBlocklist = jest
    .fn()
    .mockImplementation(
      (_ = true): Observable<PiResponse<BlocklistEntry[]>> =>
        of(MockPiResponse.fromValue<BlocklistEntry[]>(this.blocklistResource.value()?.result?.value ?? []))
    );

  removeBlocklistEntry = jest.fn().mockImplementation((_: BlocklistEntry): Observable<boolean> => of(true));

  addBlocklistEntry = jest.fn().mockImplementation(
    (request: BlockIpRequest): Observable<BlocklistEntry | null> =>
      of({
        identifier: request.ip,
        permanent: request.duration_seconds == null,
        block_expires_at: null,
        seconds_remaining: request.duration_seconds ?? null,
        block_cause: "MANUAL",
        blocked_at: ""
      })
  );
  purgeBlocklist = jest.fn().mockImplementation((): Observable<number> => of(0));

  setUserLockStatus(value: LockedUserEntry | null): void {
    this.userLockResource.set(MockPiResponse.fromValue<LockedUserEntry | null>(value));
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

  // Seed what countLockedUsers() reports for one set of states, e.g. setLockedUsersCount(["permanent"], 2).
  setLockedUsersCount(states: LockState[], count: number): void {
    this.lockedUsersCounts.set(states.join(","), count);
  }
}
