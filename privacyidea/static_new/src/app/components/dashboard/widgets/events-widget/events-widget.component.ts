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
import { EventHandler, EventService, EventServiceInterface } from "@services/event/event.service";

export interface EventPartition {
  active: EventHandler[];
  inactive: EventHandler[];
}

@Component({
  selector: "app-events-widget",
  standalone: true,
  imports: [RouterLink, WidgetStateComponent],
  templateUrl: "./events-widget.component.html",
  styleUrl: "./events-widget.component.scss"
})
export class EventsWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "events";
  static override readonly requiredAction = "eventhandling_read";
  static override readonly title = $localize`Events`;
  static override readonly icon = "flag";
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 3 };
  static override readonly minSize: WidgetSize = { cols: 4, rows: 3 };
  static override readonly maxSize: WidgetSize = { cols: 10, rows: 6 };

  protected readonly routePaths = ROUTE_PATHS;

  private readonly eventService: EventServiceInterface = inject(EventService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<PiResponse<EventHandler[]>> | null>(null);
  override readonly partialLoading = computed(() => this.dataRef()?.revalidating() ?? false);

  readonly events = computed<EventPartition>(() => {
    const all = this.dataRef()?.value()?.result?.value ?? [];
    const active: EventHandler[] = [];
    const inactive: EventHandler[] = [];
    for (const event of all) {
      if (event.active) {
        active.push(event);
      } else {
        inactive.push(event);
      }
    }
    return { active, inactive };
  });

  constructor() {
    super();
    effect(() => {
      const ref = this.dataRef();
      if (!ref) {
        return;
      }
      if (ref.error()) {
        this.state.set("error");
        return;
      }
      const value = ref.value();
      if (value !== undefined) {
        this.state.set(value.result?.status === true ? "ready" : "error");
      } else {
        this.state.set("loading");
      }
    });
  }

  override reload(): void {
    this.store.invalidate("dashboard:events");
    this.ngOnInit();
  }

  ngOnInit(): void {
    if (!this.authService.actionAllowed("eventhandling_read")) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(this.store.load("dashboard:events", () => this.eventService.getEventHandlers()));
  }
}
