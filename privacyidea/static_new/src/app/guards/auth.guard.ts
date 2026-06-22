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
import { inject, Injectable } from "@angular/core";
import { CanActivate, CanActivateChild, CanActivateFn, CanMatchFn, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";

export const adminMatch: CanMatchFn = () => inject(AuthService).role() === "admin";
export const selfServiceMatch: CanMatchFn = () => inject(AuthService).role() === "user";

/**
 * Resolve the route an authenticated user should land on. Mirrors the post-login
 * navigation: wizards first, then tokens or containers depending on role and permissions.
 */
export function resolveLandingPath(authService: AuthServiceInterface): string {
  // The wizard routes live only in the self-service route tree (selfServiceMatch), so only a
  // self-service user may be sent there. Directing any other role to a wizard path produces a
  // URL with no matching route -> '**' -> /login -> loginGuard -> the same path -> redirect loop.
  if (authService.role() === "user") {
    if (authService.tokenWizard()) {
      return ROUTE_PATHS.TOKENS_WIZARD;
    }
    if (authService.containerWizard().enabled) {
      return ROUTE_PATHS.CONTAINERS_WIZARD;
    }
    return ROUTE_PATHS.TOKENS;
  }
  if (authService.anyTokenActionAllowed()) {
    return ROUTE_PATHS.TOKENS;
  }
  if (authService.anyContainerActionAllowed()) {
    return ROUTE_PATHS.CONTAINERS;
  }
  return ROUTE_PATHS.TOKENS;
}

/**
 * Keeps authenticated users off the login page: when a session is already active (e.g.
 * restored after a full reload from switching the UI language), redirect to the landing
 * page instead of showing the login form.
 */
export const loginGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  if (!authService.isAuthenticated()) {
    return true;
  }
  return inject(Router).parseUrl(resolveLandingPath(authService));
};

@Injectable({
  providedIn: "root"
})
export class AuthGuard implements CanActivate, CanActivateChild {
  private readonly router = inject(Router);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  canActivate(): boolean {
    return this.checkAuth();
  }

  canActivateChild(): boolean {
    return this.checkAuth();
  }

  private checkAuth(): boolean {
    if (this.authService.isAuthenticated()) {
      return true;
    } else {
      this.router.navigate(["/login"]).then((r) => {
        console.warn("Navigation blocked by AuthGuard!", r);
        this.notificationService.warning("Navigation blocked by AuthGuard!");
      });
      return false;
    }
  }
}
