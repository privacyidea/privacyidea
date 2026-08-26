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
import { HttpHeaders, HttpErrorResponse, provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import {
  BlocklistEntry,
  ConditionalAccessStateService,
  LockedUsersPage,
  LockedUserEntry
} from "@services/conditional-access-state/conditional-access-state.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { UserService } from "@services/user/user.service";
import { MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockUserService } from "@testing/mock-services/mock-user-service";

environment.proxyUrl = "/api";

const BASE = "/api/conditionalaccess/";

const emptyLockedUsersPage = () =>
  MockPiResponse.fromValue<LockedUsersPage>({ locked_users: [], count: 0, current: 1, prev: null, next: null });

const lockStatus = (): LockedUserEntry => ({
  resolver: "reso1",
  uid: "uid-1",
  realm: "realm1",
  username: "alice",
  permanent: false,
  lock_expires_at: "2030-01-01T10:00:00Z",
  seconds_remaining: 120,
  locked_at: "2030-01-01T09:58:00Z"
});

const blocklistEntry = (identifier: string): BlocklistEntry => ({
  identifier,
  permanent: false,
  block_expires_at: "2030-01-01T10:00:00Z",
  seconds_remaining: 120,
  blocked_at: "2030-01-01T09:58:00Z"
});

// A fully-formed HttpErrorResponse whose nested body carries the API error message the catchError branch reads.
const errorResponse = () =>
  new HttpErrorResponse({
    status: 500,
    statusText: "Server Error",
    error: { result: { error: { message: "boom" } } }
  });

describe("ConditionalAccessStateService", () => {
  let service: ConditionalAccessStateService;
  let authService: MockAuthService;
  let content: MockContentService;
  let userService: MockUserService;
  let notification: MockNotificationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: UserService, useClass: MockUserService },
        ConditionalAccessStateService
      ]
    });
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    content = TestBed.inject(ContentService) as unknown as MockContentService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    notification = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    httpMock = TestBed.inject(HttpTestingController);
    jest.spyOn(authService, "getHeaders").mockReturnValue(new HttpHeaders());
    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    service = TestBed.inject(ConditionalAccessStateService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  const onUserDetailsRoute = () => {
    content.detailsUser.set({ username: "alice", realm: "realm1" });
    content.routeUrl.set(ROUTE_PATHS.USERS_DETAILS + "/alice");
  };

  it("is created", () => {
    expect(service).toBeTruthy();
  });

  // --- lockedUsersFilterParams / pageIndex ---

  it("keeps known filter keys verbatim and drops unknown/empty ones", () => {
    expect(service.lockedUsersFilterParams()).toEqual({});

    service.lockedUsersFilter.set(
      new FilterValue({ value: "usernames: alice realms: realm1 states: permanent,temporary foo: bar resolvers:    " })
    );
    expect(service.lockedUsersFilterParams()).toEqual({
      usernames: "alice",
      realms: "realm1",
      states: "permanent,temporary"
    });
  });

  it("resets pageIndex to 1 when the filter changes", () => {
    service.lockedUsersPageIndex.set(4);
    service.lockedUsersFilter.set(new FilterValue({ value: "usernames: bob" }));
    expect(service.lockedUsersPageIndex()).toBe(1);
  });

  it("resets pageIndex to 1 when the sort changes", () => {
    service.lockedUsersPageIndex.set(3);
    service.lockedUsersSort.set({ active: "username", direction: "asc" });
    expect(service.lockedUsersPageIndex()).toBe(1);
  });

  // --- userLockResource / userLockStatus ---

  it("loads the user lock status on the user-details route, including the resolver when set", async () => {
    userService.user.set({ ...userService.user(), resolver: "reso1" });
    onUserDetailsRoute();
    TestBed.tick();

    const req = httpMock.expectOne((r) => r.url === BASE + "lock/user");
    expect(req.request.method).toBe("GET");
    expect(req.request.params.get("user")).toBe("alice");
    expect(req.request.params.get("realm")).toBe("realm1");
    expect(req.request.params.get("resolver")).toBe("reso1");

    req.flush(MockPiResponse.fromValue(lockStatus()));
    await Promise.resolve();
    TestBed.tick();
    expect(service.userLockStatus()?.username).toBe("alice");
  });

  it("omits the resolver param when the user has none", () => {
    userService.user.set({ ...userService.user(), resolver: "" });
    onUserDetailsRoute();
    TestBed.tick();

    const req = httpMock.expectOne((r) => r.url === BASE + "lock/user");
    expect(req.request.params.has("resolver")).toBe(false);
    req.flush(MockPiResponse.fromValue<LockedUserEntry | null>(null));
  });

  it("userLockStatus is null when the user is not locked (value null)", async () => {
    onUserDetailsRoute();
    TestBed.tick();
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/user");
    req.flush(MockPiResponse.fromValue<LockedUserEntry | null>(null));
    await Promise.resolve();
    TestBed.tick();
    expect(service.userLockStatus()).toBeNull();
  });

  it("userLockStatus is null before the resource has a value", () => {
    expect(service.userLockStatus()).toBeNull();
  });

  it("does not load the user lock without the username/realm", () => {
    content.detailsUser.set({ username: "", realm: "" });
    content.routeUrl.set(ROUTE_PATHS.USERS_DETAILS + "/alice");
    TestBed.tick();
    httpMock.expectNone((r) => r.url === BASE + "lock/user");
  });

  it("does not load the user lock off the user-details route", () => {
    content.detailsUser.set({ username: "alice", realm: "realm1" });
    content.routeUrl.set(ROUTE_PATHS.TOKENS);
    TestBed.tick();
    httpMock.expectNone((r) => r.url === BASE + "lock/user");
  });

  it("does not load the user lock without the read right", () => {
    (authService.actionAllowed as jest.Mock).mockReturnValue(false);
    onUserDetailsRoute();
    TestBed.tick();
    httpMock.expectNone((r) => r.url === BASE + "lock/user");
  });

  // --- lockedUsersResource ---

  it("builds the locked-users GET with page, sort, case_insensitive and filter params", () => {
    service.lockedUsersFilter.set(new FilterValue({ value: "usernames: alice" }));
    content.routeUrl.set(ROUTE_PATHS.LOCKED_USERS);
    TestBed.tick();

    const req = httpMock.expectOne((r) => r.url === BASE + "lock/users");
    expect(req.request.method).toBe("GET");
    expect(req.request.params.get("page")).toBe("1");
    expect(req.request.params.get("page_size")).toBe("15");
    expect(req.request.params.get("sort_column")).toBe("locked_at");
    expect(req.request.params.get("sort_order")).toBe("desc");
    expect(req.request.params.get("case_insensitive")).toBe("true");
    expect(req.request.params.get("usernames")).toBe("alice");
    req.flush(emptyLockedUsersPage());
  });

  it("falls back to sort_order desc when the sort has no direction", () => {
    service.lockedUsersSort.set({ active: "username", direction: "" });
    content.routeUrl.set(ROUTE_PATHS.LOCKED_USERS);
    TestBed.tick();
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/users");
    expect(req.request.params.get("sort_column")).toBe("username");
    expect(req.request.params.get("sort_order")).toBe("desc");
    req.flush(emptyLockedUsersPage());
  });

  it("does not load locked users off the locked-users route or without the read right", () => {
    content.routeUrl.set(ROUTE_PATHS.LOCKED_USERS);
    (authService.actionAllowed as jest.Mock).mockReturnValue(false);
    TestBed.tick();
    httpMock.expectNone((r) => r.url === BASE + "lock/users");
  });

  // --- resetUserLock ---

  it("resetUserLock by uid sends a user_id payload and maps the value", () => {
    let result: boolean | undefined;
    service.resetUserLock({ uid: "uid-1", realm: "realm1", resolver: "reso1" }).subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/user" && r.method === "DELETE");
    expect(req.request.body).toEqual({ user_id: "uid-1", realm: "realm1", resolver: "reso1" });
    req.flush(MockPiResponse.fromValue(true));
    expect(result).toBe(true);
  });

  it("resetUserLock by login sends a user payload", () => {
    let result: boolean | undefined;
    service.resetUserLock({ login: "alice", realm: "realm1", resolver: "reso1" }).subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/user" && r.method === "DELETE");
    expect(req.request.body).toEqual({ user: "alice", realm: "realm1", resolver: "reso1" });
    req.flush(MockPiResponse.fromValue(false));
    expect(result).toBe(false);
  });

  it("resetUserLock returns false and notifies on error", () => {
    let result: boolean | undefined;
    service.resetUserLock({ uid: "uid-1", realm: "realm1", resolver: "reso1" }).subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/user" && r.method === "DELETE");
    req.flush(errorResponse().error, { status: 500, statusText: "Server Error" });
    expect(result).toBe(false);
    expect(notification.error).toHaveBeenCalled();
  });

  // --- countLockedUsers ---

  it("countLockedUsers asks for the smallest page of the requested states", () => {
    let count: number | undefined;
    service
      .countLockedUsers(["permanent", "temporary"])
      .subscribe((response) => (count = response.result?.value?.count));
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/users" && r.method === "GET");

    expect(req.request.params.get("states")).toBe("permanent,temporary");
    expect(req.request.params.get("page_size")).toBe("1");
    req.flush(
      MockPiResponse.fromValue<LockedUsersPage>({
        locked_users: [lockStatus()],
        count: 7,
        current: 1,
        prev: null,
        next: null
      })
    );
    expect(count).toBe(7);
  });

  // --- purgeUserLocks ---

  it("purgeUserLocks maps the removed count", () => {
    let result: number | undefined;
    service.purgeUserLocks().subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/users/purge" && r.method === "POST");
    req.flush(MockPiResponse.fromValue(3));
    expect(result).toBe(3);
  });

  it("purgeUserLocks returns 0 and notifies on error", () => {
    let result: number | undefined;
    service.purgeUserLocks().subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/users/purge" && r.method === "POST");
    req.flush(errorResponse().error, { status: 500, statusText: "Server Error" });
    expect(result).toBe(0);
    expect(notification.error).toHaveBeenCalled();
  });

  // --- blocklistResource ---

  it("loads the blocklist on the blocklist route", () => {
    content.routeUrl.set(ROUTE_PATHS.BLOCKLIST);
    TestBed.tick();
    const req = httpMock.expectOne((r) => r.url === BASE + "blocklist");
    expect(req.request.method).toBe("GET");
    req.flush(MockPiResponse.fromValue<BlocklistEntry[]>([]));
  });

  it("does not load the blocklist off route or without the read right", () => {
    content.routeUrl.set(ROUTE_PATHS.BLOCKLIST);
    (authService.actionAllowed as jest.Mock).mockReturnValue(false);
    TestBed.tick();
    httpMock.expectNone((r) => r.url === BASE + "blocklist");
  });

  // --- fetchBlocklist ---

  it("fetchBlocklist reads the list off route, including the expired entries by default", () => {
    let entries: BlocklistEntry[] | undefined;
    service.fetchBlocklist().subscribe((response) => (entries = response.result?.value));
    const req = httpMock.expectOne((r) => r.url === BASE + "blocklist" && r.method === "GET");

    expect(req.request.params.get("include_expired")).toBe("true");
    req.flush(MockPiResponse.fromValue<BlocklistEntry[]>([blocklistEntry("10.0.0.1")]));
    expect(entries).toEqual([blocklistEntry("10.0.0.1")]);
  });

  it("fetchBlocklist can ask for the enforced entries only", () => {
    service.fetchBlocklist(false).subscribe();
    const req = httpMock.expectOne((r) => r.url === BASE + "blocklist" && r.method === "GET");

    expect(req.request.params.get("include_expired")).toBe("false");
    req.flush(MockPiResponse.fromValue<BlocklistEntry[]>([]));
  });

  // --- removeBlocklistEntry ---

  it("removeBlocklistEntry URL-encodes the identifier and maps the value", () => {
    let result: boolean | undefined;
    service.removeBlocklistEntry(blocklistEntry("2001:db8::1")).subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.method === "DELETE" && r.url.startsWith(BASE + "blocklist/"));
    expect(req.request.url).toBe(BASE + "blocklist/" + encodeURIComponent("2001:db8::1"));
    req.flush(MockPiResponse.fromValue(true));
    expect(result).toBe(true);
  });

  it("removeBlocklistEntry returns false and notifies on error", () => {
    let result: boolean | undefined;
    service.removeBlocklistEntry(blocklistEntry("203.0.113.7")).subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.method === "DELETE" && r.url.startsWith(BASE + "blocklist/"));
    req.flush(errorResponse().error, { status: 500, statusText: "Server Error" });
    expect(result).toBe(false);
    expect(notification.error).toHaveBeenCalled();
  });

  // --- purgeBlocklist ---

  it("purgeBlocklist maps the removed count", () => {
    let result: number | undefined;
    service.purgeBlocklist().subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.url === BASE + "blocklist/purge" && r.method === "POST");
    req.flush(MockPiResponse.fromValue(2));
    expect(result).toBe(2);
  });

  it("purgeBlocklist returns 0 and notifies on error", () => {
    let result: number | undefined;
    service.purgeBlocklist().subscribe((v) => (result = v));
    const req = httpMock.expectOne((r) => r.url === BASE + "blocklist/purge" && r.method === "POST");
    req.flush(errorResponse().error, { status: 500, statusText: "Server Error" });
    expect(result).toBe(0);
    expect(notification.error).toHaveBeenCalled();
  });

  // --- constructor effects: surface resource errors to the notification service ---

  it("surfaces a locked-users resource error to the notification service", async () => {
    content.routeUrl.set(ROUTE_PATHS.LOCKED_USERS);
    TestBed.tick();
    const req = httpMock.expectOne((r) => r.url === BASE + "lock/users");
    req.flush(errorResponse().error, { status: 500, statusText: "Server Error" });
    await Promise.resolve();
    TestBed.tick();
    expect(notification.handleResourceError).toHaveBeenCalled();
  });
});
