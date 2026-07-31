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
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideZonelessChangeDetection } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { InfoService, NEWS_ITEM_LIMIT, NewsChannels, NewsItem, sortNewsItems } from "./info.service";

const newsUrl = environment.proxyUrl + "/info/rss";

function newsItem(title: string, pubDate: string): NewsItem {
  return {
    title: title,
    link: `https://example.com/${title}`,
    pub_date: pubDate,
    summary: `<p>${title}</p>`
  };
}

describe("sortNewsItems", () => {
  it("should return an empty list for empty channels", () => {
    expect(sortNewsItems({})).toEqual([]);
  });

  it("should map every channel entry to a list item carrying its channel name", () => {
    const channels: NewsChannels = {
      Blog: [newsItem("Release", "Mon, 20 Jul 2026 10:00:00 +0000")]
    };

    expect(sortNewsItems(channels)).toEqual([
      {
        title: "Release",
        link: "https://example.com/Release",
        channel: "Blog",
        summary: "<p>Release</p>",
        date: new Date("Mon, 20 Jul 2026 10:00:00 +0000")
      }
    ]);
  });

  it("should sort items of all channels by date descending", () => {
    const channels: NewsChannels = {
      Blog: [
        newsItem("Older", "Mon, 20 Jul 2026 10:00:00 +0000"),
        newsItem("Newest", "Fri, 24 Jul 2026 10:00:00 +0000")
      ],
      News: [newsItem("Middle", "Wed, 22 Jul 2026 10:00:00 +0000")]
    };

    expect(sortNewsItems(channels).map((item) => item.title)).toEqual(["Newest", "Middle", "Older"]);
  });

  it("should push items without a parsable date to the end", () => {
    const channels: NewsChannels = {
      Blog: [newsItem("NoDate", "not a date"), newsItem("Dated", "Mon, 20 Jul 2026 10:00:00 +0000")]
    };

    const items = sortNewsItems(channels);
    expect(items.map((item) => item.title)).toEqual(["Dated", "NoDate"]);
    expect(items[1].date).toBeNull();
  });

  it("should treat an empty pub_date as no date", () => {
    const channels: NewsChannels = { Blog: [newsItem("NoDate", "")] };

    expect(sortNewsItems(channels)[0].date).toBeNull();
  });

  it("should keep the original order of items that both have no date", () => {
    const channels: NewsChannels = { Blog: [newsItem("First", ""), newsItem("Second", "")] };

    expect(sortNewsItems(channels).map((item) => item.title)).toEqual(["First", "Second"]);
  });

  it("should tolerate a channel without items", () => {
    const channels = { Blog: null } as unknown as NewsChannels;

    expect(sortNewsItems(channels)).toEqual([]);
  });

  it("should limit the result to the default item limit", () => {
    const channels: NewsChannels = {
      Blog: Array.from({ length: NEWS_ITEM_LIMIT + 5 }, (_, index) =>
        newsItem(`Item${index}`, "Mon, 20 Jul 2026 10:00:00 +0000")
      )
    };

    expect(sortNewsItems(channels)).toHaveLength(NEWS_ITEM_LIMIT);
  });

  it("should limit the result to an explicit maximum", () => {
    const channels: NewsChannels = {
      Blog: [newsItem("A", "Fri, 24 Jul 2026 10:00:00 +0000"), newsItem("B", "Mon, 20 Jul 2026 10:00:00 +0000")]
    };

    expect(sortNewsItems(channels, 1).map((item) => item.title)).toEqual(["A"]);
  });
});

describe("InfoService", () => {
  let infoService: InfoService;
  let httpMock: HttpTestingController;
  let authMock: MockAuthService;

  const channels: NewsChannels = {
    Blog: [newsItem("Release", "Mon, 20 Jul 2026 10:00:00 +0000")],
    News: [newsItem("Training", "Wed, 22 Jul 2026 10:00:00 +0000")]
  };

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        InfoService
      ]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    httpMock = TestBed.inject(HttpTestingController);
  });

  const enableNews = (): void => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rss_age: 30 });
  };

  it("should be created", () => {
    infoService = TestBed.inject(InfoService);
    expect(infoService).toBeTruthy();
  });

  describe("newsEnabled", () => {
    it("should be false while rss_age is zero", () => {
      infoService = TestBed.inject(InfoService);
      expect(infoService.newsEnabled()).toBe(false);
    });

    it("should be true once rss_age is positive", () => {
      enableNews();
      infoService = TestBed.inject(InfoService);
      expect(infoService.newsEnabled()).toBe(true);
    });
  });

  describe("newsResource", () => {
    it("should not request the feed while the news feed is disabled", () => {
      infoService = TestBed.inject(InfoService);
      TestBed.tick();

      httpMock.expectNone(newsUrl);
    });

    it("should not request the feed while the user is not authenticated", () => {
      enableNews();
      authMock.isAuthenticated.set(false);
      infoService = TestBed.inject(InfoService);
      TestBed.tick();

      httpMock.expectNone(newsUrl);
    });

    it("should request the feed when authenticated and enabled", () => {
      enableNews();
      infoService = TestBed.inject(InfoService);
      TestBed.tick();

      const req = httpMock.expectOne(newsUrl);
      expect(req.request.method).toBe("GET");
    });

    it("should expose the loaded response", async () => {
      enableNews();
      infoService = TestBed.inject(InfoService);
      TestBed.tick();
      httpMock.expectOne(newsUrl).flush(MockPiResponse.fromValue<NewsChannels>(channels));
      await Promise.resolve();

      expect(infoService.newsResource.value()?.result?.value).toEqual(channels);
    });
  });

  describe("newsItems", () => {
    it("should be empty while the resource has no value", () => {
      infoService = TestBed.inject(InfoService);
      expect(infoService.newsItems()).toEqual([]);
    });

    it("should expose the sorted items of the loaded feed", async () => {
      enableNews();
      infoService = TestBed.inject(InfoService);
      TestBed.tick();
      httpMock.expectOne(newsUrl).flush(MockPiResponse.fromValue<NewsChannels>(channels));
      await Promise.resolve();

      expect(infoService.newsItems().map((item) => item.title)).toEqual(["Training", "Release"]);
      expect(infoService.newsItems()[0].channel).toBe("News");
    });

    it("should be empty when the response carries no value", async () => {
      enableNews();
      infoService = TestBed.inject(InfoService);
      TestBed.tick();
      httpMock.expectOne(newsUrl).flush(new MockPiResponse<NewsChannels>({ result: { status: true } }));
      await Promise.resolve();

      expect(infoService.newsItems()).toEqual([]);
    });
  });

  describe("getNews", () => {
    it("should request the feed without params by default", () => {
      infoService = TestBed.inject(InfoService);
      infoService.getNews().subscribe();

      const req = httpMock.expectOne(newsUrl);
      expect(req.request.method).toBe("GET");
      expect(req.request.params.keys()).toEqual([]);
      req.flush(MockPiResponse.fromValue<NewsChannels>(channels));
    });

    it("should pass the channel as a request param", () => {
      infoService = TestBed.inject(InfoService);
      infoService.getNews("Blog").subscribe();

      const req = httpMock.expectOne((request) => request.url === newsUrl && request.params.get("channel") === "Blog");
      req.flush(MockPiResponse.fromValue<NewsChannels>(channels));
    });

    it("should emit the response value", () => {
      infoService = TestBed.inject(InfoService);
      let received: NewsChannels | undefined;
      infoService.getNews().subscribe((response) => (received = response.result?.value));

      httpMock.expectOne(newsUrl).flush(MockPiResponse.fromValue<NewsChannels>(channels));

      expect(received).toEqual(channels);
    });

    it("should send the auth headers", () => {
      infoService = TestBed.inject(InfoService);
      infoService.getNews().subscribe();

      httpMock.expectOne(newsUrl).flush(MockPiResponse.fromValue<NewsChannels>(channels));
      expect(authMock.getHeaders).toHaveBeenCalled();
    });
  });
});
