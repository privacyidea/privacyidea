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
import { inject, Injectable } from "@angular/core";
import { CanActivate, CanActivateChild, CanMatchFn, Router } from "@angular/router";
import { AuthService, AuthServiceInterface } from "../services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../services/notification/notification.service";

export const adminMatch: CanMatchFn = () => inject(AuthService).role() === "admin";

export const selfServiceMatch: CanMatchFn = () => inject(AuthService).role() === "user";

@Injectable({
  providedIn: "root"
})
export class AuthGuard implements CanActivate, CanActivateChild {
  private readonly router: Router = inject(Router);
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
        this.notificationService.openSnackBar("Navigation blocked by AuthGuard!");
      });
      return false;
    }
  }
}
