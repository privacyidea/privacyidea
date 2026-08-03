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
import { By } from "@angular/platform-browser";
import { provideRouter } from "@angular/router";
import { routes as adminRoutes } from "@app/admin.routes";
import { ROUTE_PATHS } from "@app/route_paths";
import { routes as selfServiceRoutes } from "@app/self-service.routes";
import { NewsListComponent } from "@components/shared/news-list/news-list.component";
import { AuthService } from "@services/auth/auth.service";
import { InfoService } from "@services/info/info.service";
import { MockInfoService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { NewsComponent } from "./news.component";

describe("NewsComponent", () => {
  let fixture: ComponentFixture<NewsComponent>;
  let component: NewsComponent;
  let authMock: MockAuthService;
  let infoMock: MockInfoService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewsComponent],
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

    fixture = TestBed.createComponent(NewsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render the page heading", () => {
    expect(fixture.nativeElement.querySelector("h3").textContent).toContain("News");
  });

  it("should pass the items of the info service to the news list", () => {
    const list = fixture.debugElement.query(By.directive(NewsListComponent)).componentInstance as NewsListComponent;
    expect(list.items()).toEqual(infoMock.newsItems());
  });

  it("should render every news item of the info service", () => {
    expect(fixture.nativeElement.querySelectorAll("li.news-item")).toHaveLength(infoMock.newsItems().length);
  });

  it("should render the summaries on the news page", () => {
    const list = fixture.debugElement.query(By.directive(NewsListComponent)).componentInstance as NewsListComponent;
    expect(list.showSummary()).toBe(true);
    expect(fixture.nativeElement.querySelector(".news-summary")).not.toBeNull();
  });

  it("should update the rendered list when the info service items change", () => {
    infoMock.newsItems.set([
      {
        title: "Single entry",
        link: "https://example.com/single",
        channel: "Blog",
        summary: "",
        date: null
      }
    ]);
    fixture.detectChanges();

    const titles: Element[] = Array.from(fixture.nativeElement.querySelectorAll("a.news-title"));
    expect(titles).toHaveLength(1);
    expect(titles[0].textContent).toContain("Single entry");
  });

  it("should render the empty state when the info service has no items", () => {
    infoMock.newsItems.set([]);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".news-empty")).not.toBeNull();
  });

  describe("disabled news feed", () => {
    let disabledFixture: ComponentFixture<NewsComponent>;

    const createDisabled = (rights: string[]): ComponentFixture<NewsComponent> => {
      authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rss_age: 0, rights: rights });
      const created = TestBed.createComponent(NewsComponent);
      created.detectChanges();
      return created;
    };

    afterEach(() => disabledFixture.destroy());

    it("should replace the list with a hint when the rss_age policy disables the feed", () => {
      disabledFixture = createDisabled(["policyread"]);

      expect(disabledFixture.nativeElement.querySelector(".news-hint")).not.toBeNull();
      expect(disabledFixture.debugElement.query(By.directive(NewsListComponent))).toBeNull();
    });

    it("should link the hint to the rss_age policies for admins with policyread", () => {
      disabledFixture = createDisabled(["policyread"]);

      const link: HTMLAnchorElement = disabledFixture.nativeElement.querySelector(".news-hint a");
      expect(link.textContent).toContain("rss_age");
      expect(link.getAttribute("href")).toContain(ROUTE_PATHS.POLICIES);
      expect(decodeURIComponent(link.getAttribute("href")!)).toContain('filter="actions: rss_age"');
    });

    it("should not link the hint without the policyread right", () => {
      disabledFixture = createDisabled([]);

      expect(disabledFixture.nativeElement.querySelector(".news-hint a")).toBeNull();
      expect(disabledFixture.nativeElement.querySelector(".news-hint").textContent).toContain("rss_age");
    });
  });

  it("should be reachable under the news route for admins", () => {
    expect(adminRoutes).toContainEqual({ path: "news", component: NewsComponent });
  });

  it("should be reachable under the news route in self service", () => {
    expect(selfServiceRoutes).toContainEqual({ path: "news", component: NewsComponent });
  });

  it("should use the news route path constant", () => {
    expect(ROUTE_PATHS.NEWS).toBe("/news");
  });
});
