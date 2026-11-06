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
import { effect, inject, Injectable } from "@angular/core";
import { MatDialog } from "@angular/material/dialog";
import { NoRealmDialogComponent } from "@components/shared/no-realm-dialog/no-realm-dialog.component";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "@services/resolver/resolver.service";
import { Subscription, take } from "rxjs";

/**
 * Opens a dialog once per authenticated session (login or app start) when an administrator who may
 * create realms finds that no realm exists. The dialog points to the resolver creation if no resolver exists either. Nothing is created automatically.
 */
@Injectable()
export class NoRealmDialogService {
  private readonly dialog = inject(MatDialog);
  private readonly auth: AuthServiceInterface = inject(AuthService);
  private readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  private handled = false;
  private pendingOpen?: Subscription;

  constructor() {
    effect(() => {
      if (!this.auth.isAuthenticated()) {
        this.handled = false;
        this.pendingOpen?.unsubscribe();
        this.pendingOpen = undefined;
        return;
      }
      if (this.handled || !this.mayOpen()) {
        return;
      }
      // The resolver list decides which variant is shown, so wait for it to avoid a flicker.
      this.resolverService.loadRequested.set(true);
      if (!this.resolverService.resolversResource.hasValue() || this.resolverService.resolversResource.isLoading()) {
        return;
      }
      this.handled = true;
      this.openWhenFree();
    });
  }

  private mayOpen(): boolean {
    return (
      this.auth.isAuthenticated() &&
      this.auth.role() === "admin" &&
      this.auth.actionAllowed("resolverwrite") &&
      this.realmService.noRealm()
    );
  }

  /** A dialog already open (e.g. the welcome dialog) is not stacked on: this one follows once it is closed. */
  private openWhenFree(): void {
    if (this.dialog.openDialogs.length > 0) {
      this.pendingOpen = this.dialog.afterAllClosed.pipe(take(1)).subscribe(() => {
        this.pendingOpen = undefined;
        // The session may have ended or changed while the other dialog was open.
        if (this.mayOpen()) {
          this.openWhenFree();
        }
      });
      return;
    }
    this.dialog.open(NoRealmDialogComponent, {
      autoFocus: false,
      data: { noResolver: this.resolverService.resolverOptions().length === 0 }
    });
  }
}
