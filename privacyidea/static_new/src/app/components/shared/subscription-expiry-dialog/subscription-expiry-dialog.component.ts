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
import { Component, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MAT_DIALOG_DATA, MatDialogClose } from "@angular/material/dialog";
import { MatButton } from "@angular/material/button";

export type SubscriptionExpiryItem = {
  application: string;
  date_till: string;
  timedelta: number;
};

export type SubscriptionExpiryDialogData = {
  items: SubscriptionExpiryItem[];
};

@Component({
  selector: "app-subscription-expiry-dialog",
  standalone: true,
  imports: [CommonModule, MatDialogClose, MatButton],
  templateUrl: "./subscription-expiry-dialog.component.html",
  styleUrl: "./subscription-expiry-dialog.component.scss"
})
export class SubscriptionExpiryDialogComponent {
  readonly data = inject<SubscriptionExpiryDialogData>(MAT_DIALOG_DATA);

  remainingDays(item: SubscriptionExpiryItem): number {
    // timedelta is negative before expiry (days until expiry), positive after; clamp to zero when past expiry
    return Math.max(0, Math.ceil(-item.timedelta));
  }
}
