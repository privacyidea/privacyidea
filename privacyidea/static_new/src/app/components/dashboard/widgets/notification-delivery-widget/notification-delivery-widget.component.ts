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
import { MatTooltip } from "@angular/material/tooltip";
import { PiResponse } from "@app/app.component";
import { TableSortHeaderComponent } from "@components/dashboard/widgets/table-sort/table-sort-header.component";
import { TableSort } from "@components/dashboard/widgets/table-sort/table-sort";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import {
  NotificationChannelEntry,
  NotificationDeliveryHealth,
  SystemService,
  SystemServiceInterface
} from "@services/system/system.service";

interface NotificationDeliverySections {
  push: NotificationChannelEntry[];
  sms: NotificationChannelEntry[];
  email: NotificationChannelEntry[];
}

type NotificationDeliveryColumn = "key" | "ok" | "failed" | "error";

function createSort(): TableSort<NotificationChannelEntry, NotificationDeliveryColumn> {
  return new TableSort<NotificationChannelEntry, NotificationDeliveryColumn>({
    key: (entry) => entry.key,
    ok: (entry) => entry.ok,
    failed: (entry) => entry.failed,
    error: (entry) => entry.error
  });
}

function withDeliveries(entries: NotificationChannelEntry[] | undefined): NotificationChannelEntry[] {
  return (entries ?? []).filter((entry) => entry.total > 0).sort((a, b) => b.total - a.total);
}

@Component({
  selector: "app-notification-delivery-widget",
  standalone: true,
  imports: [MatTooltip, WidgetStateComponent, TableSortHeaderComponent],
  templateUrl: "./notification-delivery-widget.component.html",
  styleUrl: "./notification-delivery-widget.component.scss"
})
export class NotificationDeliveryWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "notification-delivery";
  static override readonly title = $localize`Notification Delivery`;
  static override readonly icon = "notifications_active";
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 6 };
  static override readonly minSize: WidgetSize = { cols: 6, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: 16, rows: 12 };

  private readonly systemService: SystemServiceInterface = inject(SystemService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<PiResponse<NotificationDeliveryHealth>> | null>(null);

  readonly sections = computed<NotificationDeliverySections>(() => {
    const delivery = this.dataRef()?.value()?.result?.value;

    return {
      push: withDeliveries(delivery?.push),
      sms: withDeliveries(delivery?.sms),
      email: withDeliveries(delivery?.email)
    };
  });

  readonly pushSort = createSort();
  readonly smsSort = createSort();
  readonly emailSort = createSort();

  readonly pushRows = computed<NotificationChannelEntry[]>(() => this.pushSort.apply(this.sections().push));
  readonly smsRows = computed<NotificationChannelEntry[]>(() => this.smsSort.apply(this.sections().sms));
  readonly emailRows = computed<NotificationChannelEntry[]>(() => this.emailSort.apply(this.sections().email));

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
    this.store.invalidate("dashboard:notification-delivery");
    this.ngOnInit();
  }

  ngOnInit(): void {
    this.dataRef.set(
      this.store.load("dashboard:notification-delivery", () => this.systemService.getNotificationDelivery())
    );
  }

  protected badgeClass(entry: NotificationChannelEntry): string {
    if (entry.error > 0) {
      return "highlight-false";
    }
    if (entry.failed > 0) {
      return "highlight-warning";
    }
    return "highlight-true";
  }
}
