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
// case-insensitively by the backend); plural to match the API query parameters (`usernames`,
// `realms`, `resolvers`), which each accept a list of values.
// `states` selects which lock state(s) to show (permanent / temporary / expired).
const LOCKED_USERS_FILTER_KEYS = ["usernames", "realms", "resolvers", "states"];

// The lock states a record can be in, as accepted by the `states` query parameter of `lockout/users`:
// permanent (no expiry), temporary (expiry still ahead) and expired (a stale row a purge removes);
// mirrors LOCK_STATES in the Python backend.
export type LockState = "permanent" | "temporary" | "expired";

// Shallow value-equality for the flat filter-params record, so a value-less key edit does not re-notify.
function shallowEqualRecord(a: Record<string, string>, b: Record<string, string>): boolean {
  const aKeys = Object.keys(a);
  return aKeys.length === Object.keys(b).length && aKeys.every((key) => a[key] === b[key]);
}

// One user-lockout record, as returned by both `lockout/user` (single lookup) and `lockout/users` (list).
export interface LockedUserEntry {
  resolver: string;
  uid: string;
  realm: string;
  username: string;
  permanent: boolean;
  lock_expires_at: string | null;
  seconds_remaining: number | null;
  locked_at: string;
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

export interface LockedUsersPage {
  locked_users: LockedUserEntry[];
  count: number;
  current: number;
  prev: number | null;
  next: number | null;
}

export interface BlocklistEntry {
  identifier: string;
  permanent: boolean;
  block_expires_at: string | null;
  seconds_remaining: number | null;
  blocked_at: string;
}

export interface ConditionalAccessStateServiceInterface {
  userLockoutResource: HttpResourceRef<PiResponse<LockedUserEntry | null> | undefined>;
  userLockoutStatus: Signal<LockedUserEntry | null>;
  resetUserLockout(request: ResetUserLockoutRequest): Observable<boolean>;
  lockedUsersFilter: WritableSignal<FilterValue>;
  lockedUsersFilterParams: () => Record<string, string>;
  lockedUsersSort: WritableSignal<Sort>;
  lockedUsersPageSize: WritableSignal<number>;
  lockedUsersPageIndex: WritableSignal<number>;
  lockedUsersResource: HttpResourceRef<PiResponse<LockedUsersPage> | undefined>;
  countLockedUsers(states: LockState[]): Observable<PiResponse<LockedUsersPage>>;
  fetchLockedUsers(states: LockState[], pageSize?: number): Observable<PiResponse<LockedUsersPage>>;
  purgeUserLockouts(): Observable<number>;
  blocklistResource: HttpResourceRef<PiResponse<BlocklistEntry[]> | undefined>;
  fetchBlocklist(includeExpired?: boolean): Observable<PiResponse<BlocklistEntry[]>>;
  removeBlocklistEntry(entry: BlocklistEntry): Observable<boolean>;
  purgeBlocklist(): Observable<number>;
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
  private readonly canReadBlocklist = computed(() => this.authService.actionAllowed("blocklist_read"));

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.userLockoutResource.error(), "user lockout state");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.lockedUsersResource.error(), "locked users");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.blocklistResource.error(), "blocklist");
    });
  }

  // Filter / sort / pagination state for the locked-users table, driving the resource params (server-side).
  lockedUsersFilter = signal(new FilterValue());

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

  lockedUsersSort = signal<Sort>({ active: "locked_at", direction: "desc" });
  lockedUsersPageSize = signal(LOCKED_USERS_DEFAULT_PAGE_SIZE);

  // 1-based (matches the API's page param); resets to the first page whenever the effective filter,
  // sort or page size changes.
  lockedUsersPageIndex = linkedSignal({
    source: () => ({
      filterParams: this.lockedUsersFilterParams(),
      pageSize: this.lockedUsersPageSize(),
      sort: this.lockedUsersSort()
    }),
    computation: () => 1
  });

  userLockoutResource = httpResource<PiResponse<LockedUserEntry | null>>(() => {
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

  userLockoutStatus = computed<LockedUserEntry | null>(() => {
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

  // Counts the locks in the given state(s) without pulling the records themselves: the page metadata
  // carries the total, so the smallest page is enough.
  // Used by the dashboard widget, whose summary needs one number per state (the paginated resource
  // above is bound to the locked-users page and its filters).
  countLockedUsers(states: LockState[]): Observable<PiResponse<LockedUsersPage>> {
    return this.http.get<PiResponse<LockedUsersPage>>(this.conditionalAccessBaseUrl + "lockout/users", {
      headers: this.authService.getHeaders(),
      params: { states: states.join(","), page: 1, page_size: 1 }
    });
  }

  // The most recently locked users in the given state(s), for callers that need the records rather than only the
  // total (the dashboard widget's highlights list).
  fetchLockedUsers(states: LockState[], pageSize = 20): Observable<PiResponse<LockedUsersPage>> {
    return this.http.get<PiResponse<LockedUsersPage>>(this.conditionalAccessBaseUrl + "lockout/users", {
      headers: this.authService.getHeaders(),
      params: { states: states.join(","), page: 1, page_size: pageSize, sort_column: "locked_at", sort_order: "desc" }
    });
  }

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

  // --- Blocklist ---

  blocklistResource = httpResource<PiResponse<BlocklistEntry[]>>(() => {
    if (!this.contentService.onBlocklist() || !this.canReadBlocklist()) {
      return undefined;
    }
    return {
      url: this.conditionalAccessBaseUrl + "blocklist",
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {}
    };
  });

  // One-off read of the whole blocklist for callers outside the blocklist page, where blocklistResource
  // deliberately does not fetch (e.g. the dashboard widget, which caches the response itself).
  fetchBlocklist(includeExpired = true): Observable<PiResponse<BlocklistEntry[]>> {
    return this.http.get<PiResponse<BlocklistEntry[]>>(this.conditionalAccessBaseUrl + "blocklist", {
      headers: this.authService.getHeaders(),
      params: { include_expired: includeExpired }
    });
  }

  removeBlocklistEntry(entry: BlocklistEntry): Observable<boolean> {
    return this.http
      .delete<
        PiResponse<boolean>
      >(this.conditionalAccessBaseUrl + "blocklist/" + encodeURIComponent(entry.identifier), { headers: this.authService.getHeaders() })
      .pipe(
        map((response) => response.result?.value ?? false),
        catchError((error) => {
          console.error("Failed to remove blocklist entry.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to remove blocklist entry. ` + message);
          return of(false);
        })
      );
  }

  purgeBlocklist(): Observable<number> {
    return this.http
      .post<PiResponse<number>>(this.conditionalAccessBaseUrl + "blocklist/purge", null, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        map((response) => response.result?.value ?? 0),
        catchError((error) => {
          console.error("Failed to purge blocklist.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to purge expired blocklist entries. ` + message);
          return of(0);
        })
      );
  }
}
