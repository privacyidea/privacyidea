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
// (permanent / temporary / expired) and replaces the former "show expired" toggle; `causes` selects
// policy vs. manual restrictions, and `error_messages` matches the wording stored on the row.
const LOCKED_USERS_FILTER_KEYS = ["usernames", "realms", "resolvers", "states", "causes", "error_messages"];

// The lock states a record can be in, as accepted by the `states` query parameter of `lock/users`:
// permanent (no expiry), temporary (expiry still ahead) and expired (a stale row a purge removes);
// mirrors LOCK_STATES in the Python backend.
export type LockState = "permanent" | "temporary" | "expired";

// Who imposed the restriction now in force: a conditional-access policy, or an administrator by hand.
// Mirrors privacyidea.lib.conditional_access.authentication_event_types.RestrictionCause.
export type LockCause = "POLICY" | "MANUAL";

// Shallow value-equality for the flat filter-params record, so a value-less key edit does not re-notify.
function shallowEqualRecord(a: Record<string, string>, b: Record<string, string>): boolean {
  const aKeys = Object.keys(a);
  return aKeys.length === Object.keys(b).length && aKeys.every((key) => a[key] === b[key]);
}

// One user-lock record, as returned by both `lock/user` (single lookup) and `lock/users` (list).
export interface LockedUserEntry {
  resolver: string;
  uid: string;
  realm: string;
  username: string;
  permanent: boolean;
  lock_expires_at: string | null;
  seconds_remaining: number | null;
  lock_cause: LockCause;
  locked_at: string;
  // What this user is told when a request is turned away, as stored when the lock was written. A snapshot, so
  // it can differ from what the stage carries now; null when the stage configured none, which is the default.
  error_message: string | null;
}

export type ResetUserLockRequest =
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

// What a manual lock needs: the user to lock, and how long for. duration_seconds omitted means a
// permanent lock, which is the backend's default and the usual intent when locking by hand.
export interface SetUserLockRequest {
  realm: string;
  resolver?: string;
  login?: string;
  uid?: string;
  duration_seconds?: number;
}

export interface BlockIpRequest {
  ip: string;
  duration_seconds?: number;
}

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
  block_cause: LockCause;
  blocked_at: string;
  // See LockedUserEntry: the wording stored on the row, not what the policy carries now.
  error_message: string | null;
}

export interface ConditionalAccessStateServiceInterface {
  userLockResource: HttpResourceRef<PiResponse<LockedUserEntry | null> | undefined>;
  userLockStatus: Signal<LockedUserEntry | null>;
  resetUserLock(request: ResetUserLockRequest): Observable<boolean>;
  setUserLock(request: SetUserLockRequest): Observable<LockedUserEntry | null>;
  lockedUsersFilter: WritableSignal<FilterValue>;
  lockedUsersFilterParams: () => Record<string, string>;
  lockedUsersSort: WritableSignal<Sort>;
  lockedUsersPageSize: WritableSignal<number>;
  lockedUsersPageIndex: WritableSignal<number>;
  lockedUsersResource: HttpResourceRef<PiResponse<LockedUsersPage> | undefined>;
  countLockedUsers(states: LockState[]): Observable<PiResponse<LockedUsersPage>>;
  fetchLockedUsers(states: LockState[], pageSize?: number): Observable<PiResponse<LockedUsersPage>>;
  purgeUserLocks(): Observable<number>;
  blocklistResource: HttpResourceRef<PiResponse<BlocklistEntry[]> | undefined>;
  fetchBlocklist(includeExpired?: boolean): Observable<PiResponse<BlocklistEntry[]>>;
  removeBlocklistEntry(entry: BlocklistEntry): Observable<boolean>;
  addBlocklistEntry(request: BlockIpRequest): Observable<BlocklistEntry | null>;
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

  private readonly canReadUserLock = computed(() => this.authService.actionAllowed("user_lock_read"));
  private readonly canReadBlocklist = computed(() => this.authService.actionAllowed("blocklist_read"));

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.userLockResource.error(), "user lock state");
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

  userLockResource = httpResource<PiResponse<LockedUserEntry | null>>(() => {
    if (!this.contentService.onUserDetails() || !this.canReadUserLock()) {
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
      url: this.conditionalAccessBaseUrl + "lock/user",
      method: "GET",
      headers: this.authService.getHeaders(),
      params
    };
  });

  userLockStatus = computed<LockedUserEntry | null>(() => {
    if (!this.userLockResource.hasValue()) {
      return null;
    }
    return this.userLockResource.value()?.result?.value ?? null;
  });

  lockedUsersResource = httpResource<PiResponse<LockedUsersPage>>(() => {
    if (!this.contentService.onLockedUsers() || !this.canReadUserLock()) {
      return undefined;
    }
    return {
      url: this.conditionalAccessBaseUrl + "lock/users",
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
    return this.http.get<PiResponse<LockedUsersPage>>(this.conditionalAccessBaseUrl + "lock/users", {
      headers: this.authService.getHeaders(),
      params: { states: states.join(","), page: 1, page_size: 1 }
    });
  }

  // The most recently locked users in the given state(s), for callers that need the records rather than only the
  // total (the dashboard widget's highlights list).
  fetchLockedUsers(states: LockState[], pageSize = 20): Observable<PiResponse<LockedUsersPage>> {
    return this.http.get<PiResponse<LockedUsersPage>>(this.conditionalAccessBaseUrl + "lock/users", {
      headers: this.authService.getHeaders(),
      params: { states: states.join(","), page: 1, page_size: pageSize, sort_column: "locked_at", sort_order: "desc" }
    });
  }

  resetUserLock(request: ResetUserLockRequest): Observable<boolean> {
    const payload =
      "uid" in request
        ? { user_id: request.uid, realm: request.realm, resolver: request.resolver }
        : { user: request.login, realm: request.realm, resolver: request.resolver };

    return this.http
      .delete<PiResponse<boolean>>(this.conditionalAccessBaseUrl + "lock/user", {
        headers: this.authService.getHeaders(),
        body: payload
      })
      .pipe(
        map((response) => response.result?.value ?? false),
        catchError((error) => {
          console.error("Failed to reset the user lock.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to reset the user lock. ` + message);
          return of(false);
        })
      );
  }

  // Lock a user by administrator decision. Returns the new lock, or null when the call failed - the
  // notification has already been shown by then, so the caller only decides whether to reload.
  setUserLock(request: SetUserLockRequest): Observable<LockedUserEntry | null> {
    const payload: Record<string, unknown> = { realm: request.realm };
    if (request.resolver) {
      payload["resolver"] = request.resolver;
    }
    if (request.uid) {
      payload["user_id"] = request.uid;
    } else {
      payload["user"] = request.login;
    }
    // Omitted rather than null: the backend reads an absent duration as "permanent".
    if (request.duration_seconds != null) {
      payload["duration_seconds"] = request.duration_seconds;
    }
    return this.http
      .post<PiResponse<LockedUserEntry>>(this.conditionalAccessBaseUrl + "lock/user", payload, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        map((response) => response.result?.value ?? null),
        catchError((error) => {
          console.error("Failed to lock user.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to lock user. ` + message);
          return of(null);
        })
      );
  }

  purgeUserLocks(): Observable<number> {
    return this.http
      .post<PiResponse<number>>(this.conditionalAccessBaseUrl + "lock/users/purge", null, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        map((response) => response.result?.value ?? 0),
        catchError((error) => {
          console.error("Failed to purge expired user locks.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to purge expired user locks. ` + message);
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

  // Block an IP by administrator decision. A never-block address is refused by the backend with an
  // explanation, which reaches the admin as the notification below rather than as a silent no-op.
  addBlocklistEntry(request: BlockIpRequest): Observable<BlocklistEntry | null> {
    const payload: Record<string, unknown> = { ip: request.ip };
    if (request.duration_seconds != null) {
      payload["duration_seconds"] = request.duration_seconds;
    }
    return this.http
      .post<PiResponse<BlocklistEntry>>(this.conditionalAccessBaseUrl + "blocklist", payload, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        map((response) => response.result?.value ?? null),
        catchError((error) => {
          console.error("Failed to block IP.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error($localize`Failed to block IP. ` + message);
          return of(null);
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
