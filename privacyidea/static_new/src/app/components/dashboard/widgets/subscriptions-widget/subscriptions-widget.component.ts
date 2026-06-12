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
import { Component, computed, effect, inject, OnInit, signal } from "@angular/core";
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { Subscription, SubscriptionService } from "@services/subscription/subscription.service";

@Component({
  selector: "app-subscriptions-widget",
  standalone: true,
  imports: [RouterLink, WidgetStateComponent],
  templateUrl: "./subscriptions-widget.component.html",
  styleUrl: "./subscriptions-widget.component.scss"
})
export class SubscriptionsWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "subscriptions";
  static override readonly title = $localize`Subscriptions`;
  static override readonly icon = "event_repeat";
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 5 };
  static override readonly minSize: WidgetSize = { cols: 8, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: 8, rows: 5 };
  static override readonly pinned = true;
  static override readonly fixedPosition = { x: 16, y: 0 };

  protected readonly routePaths = ROUTE_PATHS;

  private readonly subscriptionService = inject(SubscriptionService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<PiResponse<Record<string, Subscription>>> | null>(null);

  readonly subscriptions = computed<Subscription[]>(() => {
    const map = this.dataRef()?.value()?.result?.value ?? {};
    return Object.values(map);
  });

  constructor() {
    super();
    effect(() => {
      const ref = this.dataRef();
      if (!ref) {
        return;
      }
      const value = ref.value();
      if (value !== undefined) {
        this.state.set(value.result?.status === true ? "ready" : "error");
      } else if (ref.error()) {
        this.state.set("error");
      } else {
        this.state.set("loading");
      }
    });
  }

  ngOnInit(): void {
    if (!this.authService.actionAllowed("managesubscription")) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(this.store.load("dashboard:subscriptions", () => this.subscriptionService.getSubscriptions()));
  }
}
