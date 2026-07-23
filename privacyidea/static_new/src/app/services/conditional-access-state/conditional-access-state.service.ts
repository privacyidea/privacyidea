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
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { StringUtils } from "@utils/string.utils";
import { Observable, of } from "rxjs";
import { catchError, map } from "rxjs/operators";

const LOCKED_USERS_DEFAULT_PAGE_SIZE = 15;

// The locked-users list supports these filter keys (comma-separated / wildcard values, matched
// case-insensitively by the backend). Plural to match the API query parameters (`usernames`, `realms`,
// `resolvers`), which each accept a list of values. `states` selects the lock state(s)
// (permanent / temporary / expired) and replaces the former "show expired" toggle.
const LOCKED_USERS_FILTER_KEYS = ["usernames", "realms", "resolvers", "states"];

// Default lock-state selection: hide expired records (the "currently locked" view).
const DEFAULT_LOCKED_USERS_FILTER = "states: permanent,temporary";

// Shallow value-equality for the flat filter-params record, so a value-less key edit does not re-notify.
function shallowEqualRecord(a: Record<string, string>, b: Record<string, string>): boolean {
  const aKeys = Object.keys(a);
  return aKeys.length === Object.keys(b).length && aKeys.every((key) => a[key] === b[key]);
}

export interface UserLockoutStatus {
  resolver: string;
  uid: string;
  realm: string;
  username: string;
  permanent: boolean;
  lock_expires_at: string | null;
  seconds_remaining: number | null;
  is_locked: boolean;
  last_updated: string;
}

export type ResetUserLockoutRequest =
  | {
      uid: string;
      realm: string;
      resolver: string;
    }
  | {
      login: string;
      realm: string;
      resolver: string;
    };

export interface LockedUserEntry {
  resolver: string;
  uid: string;
  realm: string;
  username: string;
  permanent: boolean;
  lock_expires_at: string | null;
  seconds_remaining: number | null;
  is_locked: boolean;
  last_updated: string;
}

export interface LockedUsersPage {
  locked_users: LockedUserEntry[];
  count: number;
  current: number;
  prev: number | null;
  next: number | null;
}

export interface ConditionalAccessStateServiceInterface {
  userLockoutResource: HttpResourceRef<PiResponse<UserLockoutStatus | null> | undefined>;
  userLockoutStatus: Signal<UserLockoutStatus | null>;
  resetUserLockout(request: ResetUserLockoutRequest): Observable<boolean>;
  lockedUsersFilter: WritableSignal<FilterValue>;
  lockedUsersFilterParams: () => Record<string, string>;
  lockedUsersSort: WritableSignal<Sort>;
  lockedUsersPageSize: WritableSignal<number>;
  lockedUsersPageIndex: WritableSignal<number>;
  lockedUsersResource: HttpResourceRef<PiResponse<LockedUsersPage> | undefined>;
  purgeUserLockouts(): Observable<number>;
}

@Injectable()
export class ConditionalAccessStateService implements ConditionalAccessStateServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly userService: UserServiceInterface = inject(UserService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly http = inject(HttpClient);

  private readonly conditionalAccessBaseUrl = environment.proxyUrl + "/conditionalaccess/";

  private readonly canReadUserLockout = computed(() => this.authService.actionAllowed("user_lockout_read"));

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.userLockoutResource.error(), "user lockout state");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.lockedUsersResource.error(), "locked users");
    });
  }

  // Filter / sort / pagination state for the locked-users table, driving the resource params (server-side).
  // Seeded to hide expired records by default.
  lockedUsersFilter = signal(new FilterValue({ value: DEFAULT_LOCKED_USERS_FILTER }));

  // Value-based equality so adding/clearing a filter key without a value does not trigger a needless reload.
  lockedUsersFilterParams = computed<Record<string, string>>(
    () => {
      const entries = Array.from(this.lockedUsersFilter().filterMap.entries())
        .filter(([key]) => LOCKED_USERS_FILTER_KEYS.includes(key))
        .map(([key, value]) => [key, (value ?? "").toString().trim()] as const)
        .filter(([, value]) => StringUtils.validFilterValue(value));
      return Object.fromEntries(entries) as Record<string, string>;
    },
    { equal: shallowEqualRecord }
  );

  lockedUsersSort = signal<Sort>({ active: "last_updated", direction: "desc" });
  lockedUsersPageSize = signal(LOCKED_USERS_DEFAULT_PAGE_SIZE);

  // 1-based (matches the API's page param). Reset to the first page whenever the effective filter, sort,
  // page size or the show-expired toggle changes.
  lockedUsersPageIndex = linkedSignal({
    source: () => ({
      filterParams: this.lockedUsersFilterParams(),
      pageSize: this.lockedUsersPageSize(),
      sort: this.lockedUsersSort()
    }),
    computation: () => 1
  });

  userLockoutResource = httpResource<PiResponse<UserLockoutStatus | null>>(() => {
    if (!this.contentService.onUserDetails() || !this.canReadUserLockout()) {
      return undefined;
    }
    const selectedUser = this.contentService.detailsUser();
    if (!selectedUser.username || !selectedUser.realm) {
      return undefined;
    }
    const resolver = this.userService.user().resolver;
    const params: Record<string, string> = {
      user: selectedUser.username,
      realm: selectedUser.realm
    };
    if (resolver) {
      params["resolver"] = resolver;
    }
    return {
      url: this.conditionalAccessBaseUrl + "lockout/user",
      method: "GET",
      headers: this.authService.getHeaders(),
      params
    };
  });

  userLockoutStatus = computed<UserLockoutStatus | null>(() => {
    if (!this.userLockoutResource.hasValue()) {
      return null;
    }
    return this.userLockoutResource.value()?.result?.value ?? null;
  });

  lockedUsersResource = httpResource<PiResponse<LockedUsersPage>>(() => {
    if (!this.contentService.onLockedUsers() || !this.canReadUserLockout()) {
      return undefined;
    }
    return {
      url: this.conditionalAccessBaseUrl + "lockout/users",
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        page: this.lockedUsersPageIndex(),
        page_size: this.lockedUsersPageSize(),
        sort_column: this.lockedUsersSort().active,
        sort_order: this.lockedUsersSort().direction || "desc",
        // Filter values are matched case-insensitively (the identity columns are case-sensitive in the DB).
        case_insensitive: true,
        ...this.lockedUsersFilterParams()
      }
    };
  });

  resetUserLockout(request: ResetUserLockoutRequest): Observable<boolean> {
    const payload =
      "uid" in request
        ? { user_id: request.uid, realm: request.realm, resolver: request.resolver }
        : { user: request.login, realm: request.realm, resolver: request.resolver };

    return this.http
      .delete<PiResponse<boolean>>(this.conditionalAccessBaseUrl + "lockout/user", {
        headers: this.authService.getHeaders(),
        body: payload
      })
      .pipe(
        map((response) => response.result?.value ?? false),
        catchError((error) => {
          console.error("Failed to reset user lockout.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to reset user lockout. ` + message);
          return of(false);
        })
      );
  }

  purgeUserLockouts(): Observable<number> {
    return this.http
      .post<PiResponse<number>>(this.conditionalAccessBaseUrl + "lockout/users/purge", null, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        map((response) => response.result?.value ?? 0),
        catchError((error) => {
          console.error("Failed to purge user lockouts.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to purge expired user lockouts. ` + message);
          return of(0);
        })
      );
  }
}
