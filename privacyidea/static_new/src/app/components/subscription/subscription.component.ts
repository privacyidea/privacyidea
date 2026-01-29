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

import { Component, computed, inject, Signal } from "@angular/core";
import { Subscription, SubscriptionService } from "../../services/subscription/subscription.service";
import { ScrollToTopDirective } from "../shared/directives/app-scroll-to-top.directive";
import { MatIcon } from "@angular/material/icon";
import { MatButton } from "@angular/material/button";

@Component({
  selector: 'app-subscription',
  imports: [
    ScrollToTopDirective,
    MatButton,
    MatIcon
  ],
  templateUrl: './subscription.component.html',
  styleUrl: './subscription.component.scss'
})
export class SubscriptionComponent {
  protected readonly subscriptionService = inject(SubscriptionService);

  subscriptions: Signal<Subscription[]> = computed(() => {
    return this.subscriptionService.subscriptionResource?.value()?.result?.value || [] as unknown as Subscription[];
  })

  uploadSubscription() {

  }
}
