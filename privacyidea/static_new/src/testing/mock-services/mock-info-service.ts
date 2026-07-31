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
import { signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { InfoServiceInterface, NewsChannels, NewsListItem } from "@services/info/info.service";
import { of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockInfoService implements InfoServiceInterface {
  static readonly MOCK_NEWS_CHANNELS: NewsChannels = {
    "privacyIDEA Blog": [
      {
        title: "privacyIDEA 3.12 released",
        link: "https://example.com/release",
        pub_date: "Mon, 20 Jul 2026 10:00:00 +0000",
        summary: "<p>New features and fixes.</p>"
      }
    ],
    "NetKnights News": [
      {
        title: "Training dates 2026",
        link: "https://example.com/training",
        pub_date: "Wed, 22 Jul 2026 08:00:00 +0000",
        summary: "<p>Register now.</p>"
      }
    ]
  };

  readonly newsResource = new MockHttpResourceRef<PiResponse<NewsChannels> | undefined>(
    MockPiResponse.fromValue<NewsChannels>(MockInfoService.MOCK_NEWS_CHANNELS)
  );

  readonly newsEnabled = signal(true);

  readonly newsItems = signal<NewsListItem[]>([
    {
      title: "Training dates 2026",
      link: "https://example.com/training",
      channel: "NetKnights News",
      summary: "<p>Register now.</p>",
      date: new Date("2026-07-22T08:00:00Z")
    },
    {
      title: "privacyIDEA 3.12 released",
      link: "https://example.com/release",
      channel: "privacyIDEA Blog",
      summary: "<p>New features and fixes.</p>",
      date: new Date("2026-07-20T10:00:00Z")
    }
  ]);

  getNews = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<NewsChannels>(MockInfoService.MOCK_NEWS_CHANNELS)));
}
