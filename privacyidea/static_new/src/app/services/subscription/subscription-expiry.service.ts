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
import { MatDialog } from "@angular/material/dialog";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { SubscriptionService } from "./subscription.service";
import { SubscriptionExpiryDialogComponent } from "../../components/shared/subscription-expiry-dialog/subscription-expiry-dialog.component";

@Injectable({ providedIn: "root" })
export class SubscriptionExpiryService {
  private readonly dialog = inject(MatDialog);
  private readonly auth: AuthServiceInterface = inject(AuthService);
  private readonly subscriptions = inject(SubscriptionService);
  private readonly opened = signal<boolean>(false);

  private readonly thresholdDays = 3000;

  constructor() {
    effect(() => {
      const isAuth = this.auth.isAuthenticated();
      if (!isAuth || this.opened()) {
        return;
      }

      const value = this.subscriptions.subscriptionsResource.value()?.result?.value;
      const items = value ? Object.values(value) : [];

      const expiring = items
        .filter((s) => s.timedelta < 0 && Math.abs(s.timedelta) <= this.thresholdDays)
        .map((s) => ({ application: s.application, date_till: s.date_till, timedelta: s.timedelta }));

      if (expiring.length > 0) {
        this.opened.set(true);
        this.dialog.open(SubscriptionExpiryDialogComponent, {
          disableClose: false,
          autoFocus: false,
          width: "640px",
          panelClass: "global-dialog-panel",
          data: { items: expiring }
        });
      }
    });
  }
}
