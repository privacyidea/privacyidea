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
import { map, Observable, of } from "rxjs";
import { ROUTE_PATHS } from "@app/route_paths";
import { LANDING_PAGE_ROUTES } from "@core/landing-page";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { UiPreferencesService, UiPreferencesServiceInterface } from "@services/user-settings/ui-preferences.service";

export const adminMatch: CanMatchFn = () => inject(AuthService).role() === "admin";
export const selfServiceMatch: CanMatchFn = () => inject(AuthService).role() === "user";

/**
 * Resolve the route an authenticated user should land on. Mirrors the post-login
 * navigation: wizards first, then the principal's landing page.
 */
export function resolveLandingPath$(
  authService: AuthServiceInterface,
  uiPreferencesService: UiPreferencesServiceInterface
): Observable<string> {
  // The wizard routes live only in the self-service route tree (selfServiceMatch), so only a
  // self-service user may be sent there. Directing any other role to a wizard path produces a
  // URL with no matching route -> '**' -> /login -> loginGuard -> the same path -> redirect loop.
  if (authService.role() === "user") {
    if (authService.tokenWizard()) {
      return of(ROUTE_PATHS.TOKENS_WIZARD);
    }
    if (authService.containerWizard().enabled) {
      return of(ROUTE_PATHS.CONTAINERS_WIZARD);
    }
    return of(ROUTE_PATHS.TOKENS);
  }
  return uiPreferencesService.landingPage$().pipe(
    map((page) => LANDING_PAGE_ROUTES[page]),
    // The token list is the landing page's ultimate fallback, but an admin without any token
    // right and no stored preference would land on a page they cannot use -- send them to
    // containers instead when that is the only thing they can see.
    map((path) =>
      path === ROUTE_PATHS.TOKENS && !authService.anyTokenActionAllowed() && authService.anyContainerActionAllowed()
        ? ROUTE_PATHS.CONTAINERS
        : path
    )
  );
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
  const router = inject(Router);
  const uiPreferencesService = inject(UiPreferencesService);
  return resolveLandingPath$(authService, uiPreferencesService).pipe(map((path) => router.parseUrl(path)));
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
        this.notificationService.warning(
          $localize`:@@common.navigationBlockedByAuthguard:Navigation blocked by AuthGuard!`
        );
      });
      return false;
    }
  }
}
