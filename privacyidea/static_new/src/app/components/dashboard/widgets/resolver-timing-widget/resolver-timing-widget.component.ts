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
import { Resolvers, ResolverService, ResolverServiceInterface } from "@services/resolver/resolver.service";
import { ResolverTimingEntry, SystemService, SystemServiceInterface } from "@services/system/system.service";
import { forkJoin } from "rxjs";

export interface ResolverTimingRow {
  resolver: string;
  resolverType: string;
  op: string | null;
  count: number;
  avgMs: number | null;
  p95Ms: number | null;
  maxMs: number | null;
}

interface ResolverTimingResponses {
  timing: PiResponse<ResolverTimingEntry[]>;
  resolvers: PiResponse<Resolvers>;
}

function toMs(seconds: number | null | undefined): number | null {
  return seconds === null || seconds === undefined ? null : Math.round(seconds * 1000);
}

@Component({
  selector: "app-resolver-timing-widget",
  standalone: true,
  imports: [MatTooltip, WidgetStateComponent, TruncationTooltipDirective, RouterLink, TableSortHeaderComponent],
  templateUrl: "./resolver-timing-widget.component.html",
  styleUrl: "./resolver-timing-widget.component.scss"
})
export class ResolverTimingWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "resolver-timing";
  static override readonly title = $localize`Resolver Timing`;
  static override readonly icon = "speed";
  static override readonly defaultSize: WidgetSize = { cols: 12, rows: 6 };
  static override readonly minSize: WidgetSize = { cols: 10, rows: 4 };
  static override readonly maxSize: WidgetSize = { cols: 18, rows: 10 };

  private readonly systemService: SystemServiceInterface = inject(SystemService);
  private readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  readonly resolverLinkAllowed = computed(() => this.authService.actionAllowed("resolverread"));

  private readonly dataRef = signal<DashboardDataRef<ResolverTimingResponses> | null>(null);

  readonly rows = computed<ResolverTimingRow[]>(() => {
    const value = this.dataRef()?.value();
    const entries = value?.timing.result?.value ?? [];
    const configuredResolvers = value?.resolvers.result?.value ?? {};

    const activeRows: ResolverTimingRow[] = entries.map((entry) => ({
      resolver: entry.labels.resolver,
      resolverType: entry.labels.resolver_type,
      op: entry.labels.op,
      count: entry.count,
      avgMs: toMs(entry.avg),
      p95Ms: toMs(entry.p95),
      maxMs: toMs(entry.max)
    }));

    const activeNames = new Set(activeRows.map((row) => row.resolver));
    const idleRows: ResolverTimingRow[] = Object.entries(configuredResolvers)
      .filter(([name]) => !activeNames.has(name))
      .map(([name, resolver]) => ({
        resolver: name,
        resolverType: resolver.type,
        op: null,
        count: 0,
        avgMs: null,
        p95Ms: null,
        maxMs: null
      }));

    return [...activeRows, ...idleRows].sort((a, b) => (b.p95Ms ?? b.maxMs ?? 0) - (a.p95Ms ?? a.maxMs ?? 0));
  });

  readonly sort = new TableSort<ResolverTimingRow, "resolver" | "op" | "count" | "avgMs" | "p95Ms" | "maxMs">({
    resolver: (row) => row.resolver,
    op: (row) => row.op,
    count: (row) => row.count,
    avgMs: (row) => row.avgMs,
    p95Ms: (row) => row.p95Ms,
    maxMs: (row) => row.maxMs
  });

  readonly sortedRows = computed<ResolverTimingRow[]>(() => this.sort.apply(this.rows()));

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
        const ok = value.timing.result?.status === true && value.resolvers.result?.status === true;
        this.state.set(ok ? "ready" : "error");
      } else {
        this.state.set("loading");
      }
    });
  }

  override reload(): void {
    this.store.invalidate("dashboard:resolver-timing");
    this.loadData();
  }

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(): void {
    this.dataRef.set(
      this.store.load("dashboard:resolver-timing", () =>
        forkJoin({
          timing: this.systemService.getResolverTiming(),
          resolvers: this.resolverService.listResolvers()
        })
      )
    );
  }

  protected resolverLink(row: ResolverTimingRow): string | null {
    return this.resolverLinkAllowed() ? ROUTE_PATHS.USERS_RESOLVERS_DETAILS + row.resolver : null;
  }

  protected badgeClass(row: ResolverTimingRow): string {
    const value = row.p95Ms ?? row.maxMs;
    if (value === null) {
      return "highlight-disabled";
    }
    if (value >= 500) {
      return "highlight-false";
    }
    if (value >= 100) {
      return "highlight-warning";
    }
    return "highlight-true";
  }
}
