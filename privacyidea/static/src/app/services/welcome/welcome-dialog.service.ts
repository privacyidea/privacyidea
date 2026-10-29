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
import { effect, inject, Injectable, signal } from "@angular/core";
import { ComponentType } from "@angular/cdk/overlay";
import { MatDialog, MatDialogRef } from "@angular/material/dialog";
import { FreeTierDialogComponent } from "@components/shared/free-tier-dialog/free-tier-dialog.component";
import { WelcomeDialogComponent } from "@components/shared/welcome-dialog/welcome-dialog.component";
import { AuthService, AuthServiceInterface, SUBSCRIPTION_STATUS } from "@services/auth/auth.service";
import { filter } from "rxjs";

@Injectable({ providedIn: "root" })
export class WelcomeDialogService {
  private readonly dialog = inject(MatDialog);
  private readonly auth: AuthServiceInterface = inject(AuthService);
  readonly opened = signal<boolean>(false);
  // Whether the welcome decision has already been made for the current authenticated session.
  // Seeded from the bootstrap auth state so a session restored on a reload (e.g. a language
  // switch) is not treated as a fresh login and does not re-open the dialog.
  private welcomeHandled = false;

  constructor() {
    this.welcomeHandled = this.auth.isAuthenticated();
    effect(() => {
      const isAuth = this.auth.isAuthenticated();
      if (!isAuth) {
        // Logged out: allow the dialog again on the next interactive login.
        this.welcomeHandled = false;
        this.opened.set(false);
        return;
      }
      if (this.welcomeHandled) {
        return;
      }
      this.welcomeHandled = true;
      // The dialogs are for administrators. The hide_welcome_info policy hides the welcome dialog only, the free
      // tier warning is shown regardless, after the welcome dialog if both are due.
      if (this.auth.role() !== "admin") {
        return;
      }
      const freeTierExceeded = this.auth.subscriptionStatus() === SUBSCRIPTION_STATUS.FREE_TIER_EXCEEDED;
      // Every login stores a new AuthData object, so it identifies the session the dialogs belong to.
      const session = this.auth.authData();
      if (!this.auth.hideWelcome()) {
        const welcome = this.openDialog(WelcomeDialogComponent);
        if (freeTierExceeded) {
          // The welcome dialog is also closed programmatically when the session ends; the free tier
          // warning must not follow it onto the login screen or into the next session.
          welcome
            .afterClosed()
            .pipe(filter(() => this.auth.authData() === session))
            .subscribe(() => this.openDialog(FreeTierDialogComponent));
        }
      } else if (freeTierExceeded) {
        this.openDialog(FreeTierDialogComponent);
      }
    });
  }

  private openDialog<T>(component: ComponentType<T>): MatDialogRef<T> {
    this.opened.set(true);
    return this.dialog.open(component, {
      disableClose: true,
      autoFocus: false
    });
  }
}
