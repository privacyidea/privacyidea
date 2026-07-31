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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { DASHBOARD_COLUMNS, DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { InfoService, NewsChannels } from "@services/info/info.service";
import { MockInfoService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of, Subject } from "rxjs";
import { NewsWidgetComponent } from "./news-widget.component";

describe("NewsWidgetComponent", () => {
  let fixture: ComponentFixture<NewsWidgetComponent>;
  let component: NewsWidgetComponent;
  let authMock: MockAuthService;
  let infoMock: MockInfoService;

  const instance: WidgetInstance = { id: "news-1", type: "news", x: 0, y: 0, cols: 9, rows: 3 };

  const channels: NewsChannels = {
    Blog: [
      {
        title: "Older entry",
        link: "https://example.com/older",
        pub_date: "Mon, 20 Jul 2026 10:00:00 +0000",
        summary: "<p>Older</p>"
      }
    ],
    News: [
      {
        title: "Newer entry",
        link: "https://example.com/newer",
        pub_date: "Wed, 22 Jul 2026 10:00:00 +0000",
        summary: "<p>Newer</p>"
      }
    ]
  };

  const createWidget = (): ComponentFixture<NewsWidgetComponent> => {
    const created = TestBed.createComponent(NewsWidgetComponent);
    created.componentRef.setInput("instance", instance);
    created.detectChanges();
    return created;
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewsWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: InfoService, useClass: MockInfoService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rss_age: 30, rights: ["policyread"] });

    infoMock = TestBed.inject(InfoService) as unknown as MockInfoService;
    infoMock.getNews.mockReturnValue(of(MockPiResponse.fromValue<NewsChannels>(channels)));

    fixture = createWidget();
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    expect(NewsWidgetComponent.type).toBe("news");
    expect(NewsWidgetComponent.title).toBeTruthy();
    expect(NewsWidgetComponent.icon).toBe("campaign");
  });

  it("should link its title to the news page", () => {
    expect(NewsWidgetComponent.titleRoute).toBe(ROUTE_PATHS.NEWS);
  });

  it("should override the static size constraints", () => {
    expect(NewsWidgetComponent.defaultSize).toEqual({ cols: 8, rows: 3 });
    expect(NewsWidgetComponent.minSize).toEqual({ cols: 6, rows: 3 });
    expect(NewsWidgetComponent.maxSize).toEqual({ cols: DASHBOARD_COLUMNS, rows: 8 });
  });

  describe("enabled news feed", () => {
    it("should load the feed through the dashboard data store", () => {
      expect(infoMock.getNews).toHaveBeenCalledTimes(1);
      expect(TestBed.inject(DashboardDataStore).peek("dashboard:news")).not.toBeNull();
    });

    it("should become ready once the feed is loaded", () => {
      expect(component.state()).toBe("ready");
    });

    it("should expose the feed items sorted by date descending", () => {
      expect(component.items().map((item) => item.title)).toEqual(["Newer entry", "Older entry"]);
    });

    it("should render the feed items", () => {
      const titles: Element[] = Array.from(fixture.nativeElement.querySelectorAll("a.news-title"));
      expect(titles.map((element) => element.textContent!.trim())).toEqual(["Newer entry", "Older entry"]);
    });

    it("should not report the news feed as disabled", () => {
      expect(component.newsDisabled()).toBe(false);
      expect(fixture.nativeElement.querySelector(".news-hint")).toBeNull();
    });

    it("should render the empty state when the feed carries no items", () => {
      TestBed.inject(DashboardDataStore).invalidate();
      infoMock.getNews.mockReturnValue(of(MockPiResponse.fromValue<NewsChannels>({})));

      const emptyFixture = createWidget();

      expect(emptyFixture.nativeElement.querySelector(".news-empty")).not.toBeNull();
      emptyFixture.destroy();
    });

    it("should stay loading while the request is in flight", () => {
      TestBed.inject(DashboardDataStore).invalidate();
      infoMock.getNews.mockReturnValue(new Subject().asObservable());

      const loadingFixture = createWidget();

      expect(loadingFixture.componentInstance.state()).toBe("loading");
      expect(loadingFixture.componentInstance.partialLoading()).toBe(true);
      loadingFixture.destroy();
    });

    it("should report an error when the request fails", () => {
      TestBed.inject(DashboardDataStore).invalidate();
      const subject = new Subject();
      infoMock.getNews.mockReturnValue(subject.asObservable());

      const errorFixture = createWidget();
      subject.error(new Error("boom"));
      errorFixture.detectChanges();

      expect(errorFixture.componentInstance.state()).toBe("error");
      errorFixture.destroy();
    });

    it("should report an error when the response status is false", () => {
      TestBed.inject(DashboardDataStore).invalidate();
      infoMock.getNews.mockReturnValue(of(new MockPiResponse<NewsChannels>({ result: { status: false } })));

      const errorFixture = createWidget();

      expect(errorFixture.componentInstance.state()).toBe("error");
      errorFixture.destroy();
    });

    it("should invalidate the cache and load again on reload()", () => {
      infoMock.getNews.mockClear();

      component.reload();

      expect(infoMock.getNews).toHaveBeenCalledTimes(1);
    });
  });

  describe("disabled news feed", () => {
    let disabledFixture: ComponentFixture<NewsWidgetComponent>;

    beforeEach(() => {
      authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rss_age: 0, rights: ["policyread"] });
      infoMock.getNews.mockClear();
      disabledFixture = createWidget();
    });

    afterEach(() => disabledFixture.destroy());

    it("should report the news feed as disabled", () => {
      expect(disabledFixture.componentInstance.newsDisabled()).toBe(true);
    });

    it("should not request the feed", () => {
      expect(infoMock.getNews).not.toHaveBeenCalled();
    });

    it("should become ready so the hint is shown instead of a spinner", () => {
      expect(disabledFixture.componentInstance.state()).toBe("ready");
      expect(disabledFixture.nativeElement.querySelector(".news-hint")).not.toBeNull();
      expect(disabledFixture.nativeElement.querySelector("ul.news-list")).toBeNull();
    });

    it("should link the hint to the rss_age policies for admins with policyread", () => {
      const link: HTMLAnchorElement = disabledFixture.nativeElement.querySelector(".news-hint a");
      expect(link.textContent).toContain("rss_age");
      expect(link.getAttribute("href")).toContain(ROUTE_PATHS.POLICIES);
      expect(decodeURIComponent(link.getAttribute("href")!)).toContain("filter=actions: rss_age");
    });

    it("should not link the hint without the policyread right", () => {
      authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rss_age: 0, rights: [] });
      const withoutRight = createWidget();

      expect(withoutRight.componentInstance.canReadPolicies()).toBe(false);
      expect(withoutRight.nativeElement.querySelector(".news-hint a")).toBeNull();
      expect(withoutRight.nativeElement.querySelector(".news-hint").textContent).toContain("rss_age");
      withoutRight.destroy();
    });
  });
});
