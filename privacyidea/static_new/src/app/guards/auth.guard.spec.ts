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
import { MockAuthService, MockLocalService, MockNotificationService } from "../../testing/mock-services";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

const flushPromises = () => new Promise((r) => setTimeout(r, 0));

const routerMock = {
  navigate: jest.fn().mockResolvedValue(true)
} as unknown as Router;

describe("AuthGuard — CanMatch helpers", () => {
  const runMatch = (fn: any) => TestBed.runInInjectionContext(() => fn({} as Route, [] as UrlSegment[])) as boolean;

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
  });

  it("adminMatch returns true only for role \"admin\"", () => {
    const auth = TestBed.inject(AuthService) as unknown as MockAuthService;

    auth.role.set("admin");
    expect(runMatch(adminMatch)).toBe(true);

    auth.role.set("user");
    expect(runMatch(adminMatch)).toBe(false);
  });

  it("selfServiceMatch returns true only for role \"user\"", () => {
    const auth = TestBed.inject(AuthService) as unknown as MockAuthService;

    auth.role.set("user");
    expect(runMatch(selfServiceMatch)).toBe(true);

    auth.role.set("admin");
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

    jest.spyOn(console, "warn").mockImplementation(() => {
    });
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
});
