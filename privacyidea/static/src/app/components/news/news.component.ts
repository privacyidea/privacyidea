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
import { Component, computed, inject } from "@angular/core";
import { Router, RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { NewsListComponent } from "@components/shared/news-list/news-list.component";
import { WidgetState } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { InfoService, InfoServiceInterface } from "@services/info/info.service";

@Component({
  selector: "app-news",
  imports: [NewsListComponent, RouterLink, ScrollToTopDirective, WidgetStateComponent],
  templateUrl: "./news.component.html",
  styleUrl: "./news.component.scss"
})
export class NewsComponent {
  protected readonly infoService: InfoServiceInterface = inject(InfoService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly rssAgePolicyLink = this.router.createUrlTree([ROUTE_PATHS.POLICIES], {
    queryParams: { filter: '"actions: rss_age"' }
  });

  protected readonly canReadPolicies = computed(() => this.authService.actionAllowed("policyread"));

  protected readonly newsDisabled = computed(() => this.authService.rssAge() <= 0);

  protected readonly newsFetchErrorMessage = $localize`:@@news.failedToFetchNews:Failed to fetch news.`;

  protected readonly pageState = computed<WidgetState>(() => {
    const resource = this.infoService.newsResource;
    if (resource.isLoading()) {
      return "loading";
    }
    if (resource.error() !== undefined) {
      return "error";
    }
    return "ready";
  });

  constructor() {
    this.infoService.requestNewsFeed();
  }
}
