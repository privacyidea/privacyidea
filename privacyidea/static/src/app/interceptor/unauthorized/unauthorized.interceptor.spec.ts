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

import { HttpErrorResponse, HttpHandlerFn, HttpRequest } from "@angular/common/http";
import { TestBed } from "@angular/core/testing";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockAuthService, MockNotificationService } from "@testing/mock-services";
import { throwError } from "rxjs";
import { unauthorizedInterceptor } from "./unauthorized.interceptor";

describe("unauthorizedInterceptor", () => {
  const run = (req: HttpRequest<unknown>, next: HttpHandlerFn) =>
    TestBed.runInInjectionContext(() => unauthorizedInterceptor(req, next));
  let authService: MockAuthService;
  let notificationService: MockNotificationService;

  const failWith =
    (status: number): HttpHandlerFn =>
    () =>
      throwError(() => new HttpErrorResponse({ status, url: "/token/" }));

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    });
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    authService.isAuthenticated.set(true);
  });

  it("ends a session the server refuses", (done) => {
    run(new HttpRequest("GET", "/token/"), failWith(401)).subscribe({
      error: () => {
        expect(authService.logout).toHaveBeenCalled();
        expect(notificationService.warning).toHaveBeenCalled();
        done();
      }
    });
  });

  it("passes the error on rather than swallowing it", (done) => {
    run(new HttpRequest("GET", "/token/"), failWith(401)).subscribe({
      error: (error: HttpErrorResponse) => {
        expect(error.status).toBe(401);
        done();
      }
    });
  });

  it("keeps the session on any other error", (done) => {
    run(new HttpRequest("GET", "/token/"), failWith(500)).subscribe({
      error: () => {
        expect(authService.logout).not.toHaveBeenCalled();
        done();
      }
    });
  });

  it("leaves the login request alone, where 401 means a wrong password", (done) => {
    run(new HttpRequest("POST", "/auth", {}), failWith(401)).subscribe({
      error: () => {
        expect(authService.logout).not.toHaveBeenCalled();
        expect(notificationService.warning).not.toHaveBeenCalled();
        done();
      }
    });
  });

  it("stays quiet when there is no session to end", (done) => {
    authService.isAuthenticated.set(false);
    run(new HttpRequest("GET", "/token/"), failWith(401)).subscribe({
      error: () => {
        expect(authService.logout).not.toHaveBeenCalled();
        expect(notificationService.warning).not.toHaveBeenCalled();
        done();
      }
    });
  });
});
