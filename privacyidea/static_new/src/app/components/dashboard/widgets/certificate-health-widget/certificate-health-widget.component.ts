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
import { DatePipe } from "@angular/common";
import { Component, computed, effect, inject, OnInit, signal } from "@angular/core";
import { MatTooltipModule } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { TableSortHeaderComponent } from "@components/dashboard/widgets/table-sort/table-sort-header.component";
import { TableSort } from "@components/dashboard/widgets/table-sort/table-sort";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { TruncationTooltipDirective } from "@components/shared/directives/truncation-tooltip.directive";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { CertificateHealthEntry, SystemService, SystemServiceInterface } from "@services/system/system.service";

@Component({
  selector: "app-certificate-health-widget",
  standalone: true,
  imports: [
    WidgetStateComponent,
    MatTooltipModule,
    DatePipe,
    TruncationTooltipDirective,
    RouterLink,
    TableSortHeaderComponent
  ],
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
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<PiResponse<CertificateHealthEntry[]>> | null>(null);

  readonly entries = computed<CertificateHealthEntry[]>(() => this.dataRef()?.value()?.result?.value ?? []);
  readonly resolverLinkAllowed = computed(() => this.authService.actionAllowed("resolverread"));

  readonly sort = new TableSort<CertificateHealthEntry, "source" | "name" | "daysRemaining" | "status">({
    source: (entry) => entry.source,
    name: (entry) => entry.name,
    daysRemaining: (entry) => entry.days_remaining,
    status: (entry) => entry.status
  });

  readonly sortedEntries = computed<CertificateHealthEntry[]>(() => this.sort.apply(this.entries()));

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
    this.store.invalidate("dashboard:certificate-health");
    this.ngOnInit();
  }

  ngOnInit(): void {
    this.dataRef.set(this.store.load("dashboard:certificate-health", () => this.systemService.getCertificateHealth()));
  }

  protected resolverLink(entry: CertificateHealthEntry): string | null {
    if (!this.resolverLinkAllowed() || !entry.source.endsWith("-resolver")) {
      return null;
    }
    return ROUTE_PATHS.USERS_RESOLVERS_DETAILS + entry.name;
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
