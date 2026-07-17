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
import { PiResponse } from "@app/app.component";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { SmsGateway, SmsGatewayService, SmsGatewayServiceInterface } from "@services/sms-gateway/sms-gateway.service";
import { SmtpServers, SmtpService, SmtpServiceInterface } from "@services/smtp/smtp.service";
import {
  NotificationChannelEntry,
  NotificationDeliveryHealth,
  SystemService,
  SystemServiceInterface
} from "@services/system/system.service";
import { forkJoin } from "rxjs";

const FIREBASE_PROVIDER_MODULE = "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider";

interface NotificationDeliverySections {
  push: NotificationChannelEntry[];
  sms: NotificationChannelEntry[];
  email: NotificationChannelEntry[];
}

interface NotificationDeliveryResponses {
  delivery: PiResponse<NotificationDeliveryHealth>;
  gateways: PiResponse<SmsGateway[]>;
  smtp: PiResponse<SmtpServers>;
}

function mergeConfigured(names: string[], entries: NotificationChannelEntry[]): NotificationChannelEntry[] {
  const byKey = new Map(entries.map((entry) => [entry.key, entry]));
  const configured = names.map((name) => byKey.get(name) ?? { key: name, ok: 0, failed: 0, error: 0, total: 0 });
  const configuredNames = new Set(names);
  const unconfigured = entries.filter((entry) => !configuredNames.has(entry.key));
  return [...configured, ...unconfigured].sort((a, b) => b.total - a.total);
}

@Component({
  selector: "app-notification-delivery-widget",
  standalone: true,
  imports: [WidgetStateComponent],
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
  private readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  private readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<NotificationDeliveryResponses> | null>(null);

  readonly sections = computed<NotificationDeliverySections>(() => {
    const value = this.dataRef()?.value();
    const delivery = value?.delivery.result?.value;
    const gateways = value?.gateways.result?.value ?? [];
    const smtpIdentifiers = Object.keys(value?.smtp.result?.value ?? {});

    const pushNames = gateways.filter((gateway) => gateway.providermodule === FIREBASE_PROVIDER_MODULE).map((g) => g.name);
    const smsNames = gateways.filter((gateway) => gateway.providermodule !== FIREBASE_PROVIDER_MODULE).map((g) => g.name);

    return {
      push: mergeConfigured(pushNames, delivery?.push ?? []),
      sms: mergeConfigured(smsNames, delivery?.sms ?? []),
      email: mergeConfigured(smtpIdentifiers, delivery?.email ?? [])
    };
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
        const ok =
          value.delivery.result?.status === true &&
          value.gateways.result?.status === true &&
          value.smtp.result?.status === true;
        this.state.set(ok ? "ready" : "error");
      } else if (ref.error()) {
        this.state.set("error");
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
      this.store.load("dashboard:notification-delivery", () =>
        forkJoin({
          delivery: this.systemService.getNotificationDelivery(),
          gateways: this.smsGatewayService.listSmsGateways(),
          smtp: this.smtpService.listSmtpServers()
        })
      )
    );
  }

  protected badgeClass(entry: NotificationChannelEntry): string {
    if (entry.total === 0) {
      return "highlight-disabled";
    }
    if (entry.error > 0) {
      return "highlight-false";
    }
    if (entry.failed > 0) {
      return "highlight-warning";
    }
    return "highlight-true";
  }
}
