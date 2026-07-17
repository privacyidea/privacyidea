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
import { CertificateHealthEntry, SystemService, SystemServiceInterface } from "@services/system/system.service";

@Component({
  selector: "app-certificate-health-widget",
  standalone: true,
  imports: [WidgetStateComponent],
  templateUrl: "./certificate-health-widget.component.html",
  styleUrl: "./certificate-health-widget.component.scss"
})
export class CertificateHealthWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "certificate-health";
  static override readonly title = $localize`Certificate Health`;
  static override readonly icon = "verified_user";
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 5 };
  static override readonly minSize: WidgetSize = { cols: 5, rows: 4 };
  static override readonly maxSize: WidgetSize = { cols: 16, rows: 10 };

  private readonly systemService: SystemServiceInterface = inject(SystemService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<PiResponse<CertificateHealthEntry[]>> | null>(null);

  readonly entries = computed<CertificateHealthEntry[]>(() => this.dataRef()?.value()?.result?.value ?? []);

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

  override reload(): void {
    this.store.invalidate("dashboard:certificate-health");
    this.ngOnInit();
  }

  ngOnInit(): void {
    this.dataRef.set(this.store.load("dashboard:certificate-health", () => this.systemService.getCertificateHealth()));
  }

  protected badgeClass(status: CertificateHealthEntry["status"]): string {
    switch (status) {
      case "ok":
        return "highlight-true";
      case "warning":
        return "highlight-warning";
      case "critical":
      case "expired":
        return "highlight-false";
      default:
        return "highlight-disabled";
    }
  }
}
