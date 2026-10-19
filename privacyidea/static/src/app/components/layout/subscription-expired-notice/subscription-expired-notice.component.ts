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
import { Component, computed, inject } from "@angular/core";
import { RouterLink } from "@angular/router";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ROUTE_PATHS } from "@app/route_paths";

// subscription_status value of an invalid subscription: expired, or more tokens in use than the subscription allows
const SUBSCRIPTION_INVALID = 2;

@Component({
  selector: "app-subscription-expired-notice",
  standalone: true,
  imports: [RouterLink],
  templateUrl: "./subscription-expired-notice.component.html",
  styleUrl: "./subscription-expired-notice.component.scss"
})
export class SubscriptionExpiredNoticeComponent {
  private readonly authService: AuthServiceInterface = inject(AuthService);

  protected readonly subscriptionPath = ROUTE_PATHS.SUBSCRIPTION;
  // The subscription page is an admin page, so the warning is for administrators only.
  readonly visible = computed(
    () => this.authService.role() === "admin" && this.authService.subscriptionStatus() === SUBSCRIPTION_INVALID
  );
}
