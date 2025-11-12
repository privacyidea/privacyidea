/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { TestBed } from "@angular/core/testing";
import { Route, Router, UrlSegment } from "@angular/router";
import { AuthService } from "../services/auth/auth.service";
import { NotificationService } from "../services/notification/notification.service";
import { adminMatch, AuthGuard, selfServiceMatch } from "./auth.guard";
import { MockLocalService, MockNotificationService } from "../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockAuthService } from "../../testing/mock-services/mock-auth-service";

const flushPromises = () => new Promise((r) => setTimeout(r, 0));

const routerMock = {
  navigate: jest.fn().mockResolvedValue(true)
} as unknown as Router;

describe("AuthGuard — CanMatch helpers", () => {
  const runMatch = (fn: any) => TestBed.runInInjectionContext(() => fn({} as Route, [] as UrlSegment[])) as boolean;
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
        { provide: Router, useValue: routerMock },
        { provide: NotificationService, useClass: MockNotificationService },
        MockLocalService,
        MockNotificationService
      ]
    });

    guard = TestBed.inject(AuthGuard);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    jest.spyOn(console, "warn").mockImplementation(() => {});
    (routerMock.navigate as jest.Mock).mockClear();
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
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Navigation blocked by AuthGuard!");
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

    expect(notificationService.openSnackBar).toHaveBeenCalledTimes(2);
    expect(notificationService.openSnackBar).toHaveBeenNthCalledWith(1, "Navigation blocked by AuthGuard!");
    expect(notificationService.openSnackBar).toHaveBeenNthCalledWith(2, "Navigation blocked by AuthGuard!");
  });

  it("does not show snackbar if router.navigate never resolves (simulates failure without unhandled rejection)", async () => {
    authService.isAuthenticated.set(false);

    (routerMock.navigate as jest.Mock).mockImplementationOnce(() => new Promise<boolean>(() => {}));

    expect(guard.canActivate()).toBe(false);
    expect(routerMock.navigate).toHaveBeenCalledWith(["/login"]);

    await flushPromises();

    expect(notificationService.openSnackBar).not.toHaveBeenCalled();
  });
});
