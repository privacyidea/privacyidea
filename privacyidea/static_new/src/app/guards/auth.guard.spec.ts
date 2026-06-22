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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import {
  ActivatedRouteSnapshot,
  CanMatchFn,
  provideRouter,
  Route,
  Router,
  RouterStateSnapshot,
  UrlSegment,
  UrlTree
} from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockAuthService, MockLocalService, MockNotificationService, MockRouter } from "@testing/mock-services";
import { adminMatch, AuthGuard, loginGuard, resolveLandingPath, selfServiceMatch } from "./auth.guard";

const flushPromises = () => new Promise((r) => setTimeout(r, 0));

let routerMock: MockRouter;

describe("AuthGuard — CanMatch helpers", () => {
  const runMatch = (fn: CanMatchFn) =>
    TestBed.runInInjectionContext(() => fn({} as Route, [] as UrlSegment[])) as boolean;
  let authMock: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    });

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  it('adminMatch returns true only for role "admin"', () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "admin" });
    expect(runMatch(adminMatch)).toBe(true);

    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "user" });
    expect(runMatch(adminMatch)).toBe(false);
  });

  it('selfServiceMatch returns true only for role "user"', () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "user" });
    expect(runMatch(selfServiceMatch)).toBe(true);

    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "admin" });
    expect(runMatch(selfServiceMatch)).toBe(false);
  });

  it("adminMatch/selfServiceMatch are false for unknown role", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "" });
    expect(authMock.role()).toBe("");
    expect(runMatch(adminMatch)).toBe(false);
    expect(runMatch(selfServiceMatch)).toBe(false);
  });
});

describe("AuthGuard class", () => {
  let guard: AuthGuard;
  let authService: MockAuthService;
  let notificationService: MockNotificationService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        AuthGuard,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: Router, useClass: MockRouter },
        { provide: NotificationService, useClass: MockNotificationService },
        MockLocalService,
        MockNotificationService
      ]
    });

    guard = TestBed.inject(AuthGuard);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    routerMock = TestBed.inject(Router) as unknown as MockRouter;
    routerMock.navigate.mockResolvedValue(true);

    jest.spyOn(console, "warn").mockReturnValue();
  });

  it("is created", () => {
    expect(guard).toBeTruthy();
  });

  it("allows activation when user is authenticated", () => {
    authService.isAuthenticated.set(true);

    expect(guard.canActivate()).toBe(true);
    expect(guard.canActivateChild()).toBe(true);
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });

  it("blocks activation and redirects to /login when not authenticated", async () => {
    authService.isAuthenticated.set(false);

    expect(guard.canActivate()).toBe(false);
    expect(guard.canActivateChild()).toBe(false);
    expect(routerMock.navigate).toHaveBeenCalledWith(["/login"]);

    await flushPromises();
    expect(notificationService.warning).toHaveBeenCalledWith("Navigation blocked by AuthGuard!");
  });

  it("calls navigate and shows snackbar twice when both canActivate + canActivateChild deny access", async () => {
    authService.isAuthenticated.set(false);
    (routerMock.navigate as jest.Mock).mockResolvedValue(true);

    expect(guard.canActivate()).toBe(false);
    expect(guard.canActivateChild()).toBe(false);

    expect(routerMock.navigate).toHaveBeenCalledTimes(2);
    expect(routerMock.navigate).toHaveBeenNthCalledWith(1, ["/login"]);
    expect(routerMock.navigate).toHaveBeenNthCalledWith(2, ["/login"]);

    await flushPromises(); // resolve both .then handlers

    expect(notificationService.warning).toHaveBeenCalledTimes(2);
    expect(notificationService.warning).toHaveBeenNthCalledWith(1, "Navigation blocked by AuthGuard!");
    expect(notificationService.warning).toHaveBeenNthCalledWith(2, "Navigation blocked by AuthGuard!");
  });

  it("does not show snackbar if router.navigate never resolves (simulates failure without unhandled rejection)", async () => {
    authService.isAuthenticated.set(false);

    (routerMock.navigate as jest.Mock).mockImplementationOnce(() => new Promise<boolean>(() => undefined));

    expect(guard.canActivate()).toBe(false);
    expect(routerMock.navigate).toHaveBeenCalledWith(["/login"]);

    await flushPromises();

    expect(notificationService.warning).not.toHaveBeenCalled();
  });
});

describe("resolveLandingPath", () => {
  let authMock: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [{ provide: AuthService, useClass: MockAuthService }]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  const landingPath = () => resolveLandingPath(authMock as unknown as AuthServiceInterface);

  it("sends a self-service user with the token wizard enabled to the token wizard", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "user", token_wizard: true });
    expect(landingPath()).toBe(ROUTE_PATHS.TOKENS_WIZARD);
  });

  it("falls back to the tokens page for a regular admin", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "admin", token_wizard: false });
    expect(landingPath()).toBe(ROUTE_PATHS.TOKENS);
  });

  it("does NOT send a non-self-service user to a wizard route even when a wizard is enabled", () => {
    // Wizard routes exist only for self-service; routing an admin there would loop via '**'.
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "admin", token_wizard: true });
    expect(landingPath()).toBe(ROUTE_PATHS.TOKENS);
  });
});

describe("loginGuard", () => {
  const runGuard = () =>
    TestBed.runInInjectionContext(() => loginGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot));
  let authMock: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  it("allows the login route when not authenticated", () => {
    authMock.isAuthenticated.set(false);
    expect(runGuard()).toBe(true);
  });

  it("redirects authenticated users to their landing page", () => {
    authMock.isAuthenticated.set(true);
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "admin" });

    const result = runGuard();
    expect(result).toBeInstanceOf(UrlTree);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe(ROUTE_PATHS.TOKENS);
  });
});
