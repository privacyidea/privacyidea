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
import { Router, RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { NewsListComponent } from "@components/shared/news-list/news-list.component";
import { DASHBOARD_COLUMNS, DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { InfoService, InfoServiceInterface, NewsChannels, sortNewsItems } from "@services/info/info.service";

@Component({
  selector: "app-news-widget",
  standalone: true,
  imports: [NewsListComponent, RouterLink, WidgetStateComponent],
  templateUrl: "./news-widget.component.html",
  styleUrl: "./news-widget.component.scss"
})
export class NewsWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "news";
  static override readonly title = $localize`News`;
  static override readonly icon = "campaign";
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 3 };
  static override readonly minSize: WidgetSize = { cols: 6, rows: 3 };
  static override readonly maxSize: WidgetSize = { cols: DASHBOARD_COLUMNS, rows: 8 };

  private readonly infoService: InfoServiceInterface = inject(InfoService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);
  private readonly router = inject(Router);

  protected readonly rssAgePolicyLink = this.router.createUrlTree([ROUTE_PATHS.POLICIES], {
    queryParams: { filter: '"actions: rss_age"' }
  });

  protected readonly canReadPolicies = computed(() => this.authService.actionAllowed("policyread"));

  readonly newsDisabled = computed(() => this.authService.rssAge() <= 0);

  override readonly canReload = computed(() => !this.newsDisabled());
  override readonly titleRoute = computed(() => (this.newsDisabled() ? null : ROUTE_PATHS.NEWS));

  private readonly dataRef = signal<DashboardDataRef<PiResponse<NewsChannels>> | null>(null);
  override readonly partialLoading = computed(() => this.dataRef()?.revalidating() ?? false);

  readonly items = computed(() => sortNewsItems(this.dataRef()?.value()?.result?.value ?? {}));

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
    this.ngOnInit();
  }

  ngOnInit(): void {
    if (this.newsDisabled()) {
      this.state.set("ready");
      return;
    }
    this.dataRef.set(this.store.load("dashboard:news", () => this.infoService.getNews()));
  }
}
