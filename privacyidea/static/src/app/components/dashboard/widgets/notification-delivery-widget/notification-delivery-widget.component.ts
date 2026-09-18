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
import { Component, computed, effect, inject, signal, TemplateRef, viewChild } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";
import { PiResponse } from "@app/app.component";
import { DEFAULT_METRICS_WINDOW, METRICS_WINDOWS, MetricsWindow } from "@components/dashboard/widgets/metrics-window";
import { TableSortHeaderComponent } from "@components/dashboard/widgets/table-sort/table-sort-header.component";
import { TableSort } from "@components/dashboard/widgets/table-sort/table-sort";
import { WidgetRangeSetting } from "@components/dashboard/widgets/widget-range-setting";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { WidgetWindowPickerComponent } from "@components/dashboard/widgets/window-picker/widget-window-picker.component";
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
  imports: [MatTooltip, WidgetStateComponent, TableSortHeaderComponent, WidgetWindowPickerComponent],
  templateUrl: "./notification-delivery-widget.component.html",
  styleUrl: "./notification-delivery-widget.component.scss"
})
export class NotificationDeliveryWidgetComponent extends DashboardWidget {
  static override readonly type = "notification-delivery";
  static override readonly title = $localize`:@@dashboard.notificationDelivery:Notification Delivery`;
  static override readonly icon = "notifications_active";
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 6 };
  static override readonly minSize: WidgetSize = { cols: 6, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: 16, rows: 12 };

  // Read by the widget frame, which renders these in its header.
  override readonly headerActions = viewChild<TemplateRef<unknown>>("headerActions");

  protected readonly windows = METRICS_WINDOWS;

  private readonly systemService: SystemServiceInterface = inject(SystemService);
  private readonly store = inject(DashboardDataStore);

  private readonly windowSetting = new WidgetRangeSetting<MetricsWindow>(
    this.instance,
    METRICS_WINDOWS,
    DEFAULT_METRICS_WINDOW
  );
  readonly selectedWindow = this.windowSetting.selected.asReadonly();

  private readonly dataRef = signal<DashboardDataRef<PiResponse<NotificationDeliveryHealth>> | null>(null);
  // The store key currently in use, so the previous window's entry can be dropped when the window changes.
  private storeKey: string | null = null;

  override readonly refreshFailed = computed(() => {
    const ref = this.dataRef();
    return !!ref && ref.error() && ref.value() !== undefined;
  });

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
      const value = ref.value();
      if (value === undefined) {
        this.state.set(ref.error() ? "error" : "loading");
        return;
      }
      this.state.set(value.result?.status === true ? "ready" : "error");
    });
    // Refetches whenever the window changes, and on the first run, which is what draws the widget.
    effect(() => this.loadData(this.selectedWindow()));
  }

  override reload(): void {
    this.loadData(this.selectedWindow());
  }

  selectWindow(id: string): void {
    this.windowSetting.select(id);
  }

  private loadData(window: MetricsWindow): void {
    const key = `dashboard:notification-delivery:${window.id}`;
    // Each window needs a key of its own, so switching shows a loading state rather than the previous window's
    // numbers. The entry left behind has to go, though: DashboardDataStore.refreshAll() refetches every entry it
    // holds, so a stale key would keep re-querying a window nobody is looking at on each dashboard refresh.
    if (this.storeKey && this.storeKey !== key) {
      this.store.invalidate(this.storeKey);
    }
    this.storeKey = key;
    this.dataRef.set(this.store.load(key, () => this.systemService.getNotificationDelivery(window.seconds)));
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
