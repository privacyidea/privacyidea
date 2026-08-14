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
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable, Signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { Observable } from "rxjs";

export interface NewsItem {
  title: string;
  link: string;
  pub_date: string;
  summary: string;
}

export type NewsChannels = Record<string, NewsItem[]>;

export interface NewsListItem {
  title: string;
  link: string;
  channel: string;
  summary: string;
  date: Date | null;
}

export function sortNewsItems(channels: NewsChannels): NewsListItem[] {
  return Object.entries(channels)
    .flatMap(([channel, items]) =>
      (items ?? []).map((item) => ({
        title: item.title,
        link: item.link,
        channel: channel,
        summary: item.summary,
        date: parseNewsDate(item.pub_date)
      }))
    )
    .sort(byDateDescending);
}

function parseNewsDate(value: string): Date | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function byDateDescending(a: NewsListItem, b: NewsListItem): number {
  const aTime = a.date?.getTime();
  const bTime = b.date?.getTime();
  if (aTime === undefined) {
    return bTime === undefined ? 0 : 1;
  }
  if (bTime === undefined) {
    return -1;
  }
  return bTime - aTime;
}

export interface InfoServiceInterface {
  readonly newsResource: HttpResourceRef<PiResponse<NewsChannels> | undefined>;
  readonly newsItems: Signal<NewsListItem[]>;
  readonly newsEnabled: Signal<boolean>;

  getNews(channel?: string): Observable<PiResponse<NewsChannels>>;
}

@Injectable({ providedIn: "root" })
export class InfoService implements InfoServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly http = inject(HttpClient);

  private readonly infoBaseUrl = environment.proxyUrl + "/info";

  readonly newsEnabled = computed(() => this.authService.rssAge() > 0);

  readonly newsResource = httpResource<PiResponse<NewsChannels>>(() => {
    if (!this.authService.isAuthenticated() || !this.newsEnabled()) {
      return undefined;
    }
    return {
      url: `${this.infoBaseUrl}/rss`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly newsItems = computed(() => sortNewsItems(this.newsResource.value()?.result?.value ?? {}));

  getNews(channel?: string): Observable<PiResponse<NewsChannels>> {
    return this.http.get<PiResponse<NewsChannels>>(`${this.infoBaseUrl}/rss`, {
      headers: this.authService.getHeaders(),
      params: channel ? { channel } : {}
    });
  }
}
