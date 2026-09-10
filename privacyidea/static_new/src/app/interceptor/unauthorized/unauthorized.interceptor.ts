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

import { HttpErrorResponse, HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { catchError, throwError } from "rxjs";

/**
 * Ends a session the server no longer accepts. A stored token can stop working without this tab
 * doing anything -- another tab of a browser-wide session logged out, the token was revoked by
 * an expiry the browser did not see, or the server was restarted with a new secret -- and the
 * WebUI would otherwise keep rendering an authenticated page whose every request fails.
 */
export const unauthorizedInterceptor: HttpInterceptorFn = (req, next) => {
  const authService: AuthServiceInterface = inject(AuthService);
  const notificationService: NotificationServiceInterface = inject(NotificationService);
  return next(req).pipe(
    catchError((error: unknown) => {
      // Only for a session that the UI still believes in: the login request answers 401 for a
      // wrong password, and a 401 on the login page has no session to end. Parallel failures
      // reach the second check with isAuthenticated() already false, so this runs once.
      if (
        error instanceof HttpErrorResponse &&
        error.status === 401 &&
        !isLoginRequest(req.url) &&
        authService.isAuthenticated()
      ) {
        notificationService.warning(
          $localize`:@@common.sessionNoLongerValid:Your session is no longer valid. Please log in again.`
        );
        authService.logout();
      }
      return throwError(() => error);
    })
  );
};

function isLoginRequest(url: string): boolean {
  return url.endsWith("/auth") || url.includes("/auth/");
}
