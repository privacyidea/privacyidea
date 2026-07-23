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
import { DASHBOARD_COLUMNS, DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";

export interface PolicyPartition {
  active: string[];
  inactive: string[];
}

@Component({
  selector: "app-policies-widget",
  standalone: true,
  imports: [RouterLink, WidgetStateComponent],
  templateUrl: "./policies-widget.component.html",
  styleUrl: "./policies-widget.component.scss"
})
export class PoliciesWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "policies";
  static override readonly requiredAction = "policyread";
  static override readonly title = $localize`Policies`;
  static override readonly icon = "gavel";
  static override readonly defaultSize: WidgetSize = { cols: 10, rows: 5 };
  static override readonly minSize: WidgetSize = { cols: 6, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: DASHBOARD_COLUMNS, rows: 8 };

  protected readonly routePaths = ROUTE_PATHS;

  private readonly policyService: PolicyServiceInterface = inject(PolicyService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<PiResponse<PolicyDetail[]>> | null>(null);
  override readonly partialLoading = computed(() => this.dataRef()?.revalidating() ?? false);

  readonly policies = computed<PolicyPartition>(() => {
    const all = this.dataRef()?.value()?.result?.value ?? [];
    const active: string[] = [];
    const inactive: string[] = [];
    for (const policy of all) {
      if (policy.active) {
        active.push(policy.name);
      } else {
        inactive.push(policy.name);
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
    this.store.invalidate("dashboard:policies");
    this.ngOnInit();
  }

  ngOnInit(): void {
    if (!this.authService.actionAllowed("policyread")) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(this.store.load("dashboard:policies", () => this.policyService.getPolicies()));
  }
}
