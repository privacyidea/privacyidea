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
import { Component, OnInit, computed, effect, inject, signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { DASHBOARD_COLUMNS, DashboardWidget, WidgetSize } from "@models/dashboard";
import { Audit, AuditData, AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { forkJoin } from "rxjs";

@Component({
  selector: "app-administration-widget",
  standalone: true,
  imports: [DatePipe, WidgetStateComponent],
  templateUrl: "./administration-widget.component.html",
  styleUrl: "./administration-widget.component.scss"
})
export class AdministrationWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "administration";
  static override readonly requiredAction = "auditlog";
  static override readonly title = $localize`Administration`;
  static override readonly icon = "supervised_user_circle";
  static override readonly defaultSize: WidgetSize = { cols: 10, rows: 6 };
  static override readonly minSize: WidgetSize = { cols: 7, rows: 4 };
  static override readonly maxSize: WidgetSize = { cols: DASHBOARD_COLUMNS, rows: 8 };

  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  private readonly store = inject(DashboardDataStore);

  private readonly adminAreas = ["system", "resolver", "realm", "policy", "event"];

  private readonly dataRef = signal<DashboardDataRef<PiResponse<Audit>[]> | null>(null);

  readonly entries = computed<AuditData[]>(() => {
    const responses = this.dataRef()?.value() ?? [];
    const collected: AuditData[] = [];
    for (const response of responses) {
      const auditdata = response?.result?.value?.auditdata ?? [];
      for (const entry of auditdata) {
        collected.push(entry);
      }
    }
    collected.sort((a, b) => {
      if ((a.date ?? "") < (b.date ?? "")) return 1;
      if ((b.date ?? "") < (a.date ?? "")) return -1;
      return 0;
    });
    return collected.slice(0, 5);
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
        this.state.set(value.every((response) => response.result?.status === true) ? "ready" : "error");
      } else if (ref.error()) {
        this.state.set("error");
      } else {
        this.state.set("loading");
      }
    });
  }

  ngOnInit(): void {
    if (!this.authService.actionAllowed("auditlog")) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(
      this.store.load("dashboard:administration", () =>
        forkJoin(
          this.adminAreas.map((area) =>
            this.auditService.fetchAuditPage({ timelimit: "1d", action: "POST /" + area + "*" })
          )
        )
      )
    );
  }
}
