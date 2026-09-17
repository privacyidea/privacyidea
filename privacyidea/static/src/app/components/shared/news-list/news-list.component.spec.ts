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
import { formatDate } from "@angular/common";
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NewsListItem } from "@services/info/info.service";
import { NewsListComponent } from "./news-list.component";

describe("NewsListComponent", () => {
  let fixture: ComponentFixture<NewsListComponent>;
  let component: NewsListComponent;

  const items: NewsListItem[] = [
    {
      title: "Training dates 2026",
      link: "https://example.com/training",
      channel: "NetKnights News",
      summary: "<p>Register <b>now</b>.</p>",
      date: new Date(2026, 6, 22, 8, 0, 0)
    },
    {
      title: "privacyIDEA 3.12 released",
      link: "https://example.com/release",
      channel: "privacyIDEA Blog",
      summary: "<p>New features.</p>",
      date: null
    }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewsListComponent],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();

    fixture = TestBed.createComponent(NewsListComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("items", items);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should not show summaries by default", () => {
    expect(component.showSummary()).toBe(false);
  });

  it("should render one list entry per item", () => {
    expect(fixture.nativeElement.querySelectorAll("li.news-item")).toHaveLength(2);
  });

  it("should render the channel of every item", () => {
    const channels: string[] = Array.from(
      fixture.nativeElement.querySelectorAll(".news-channel") as NodeListOf<Element>
    ).map((element) => element.textContent!.trim());
    expect(channels).toEqual(["NetKnights News", "privacyIDEA Blog"]);
  });

  it("should render the title as a link to the news item", () => {
    const link: HTMLAnchorElement = fixture.nativeElement.querySelector("a.news-title");
    expect(link.textContent!.trim()).toBe("Training dates 2026");
    expect(link.getAttribute("href")).toBe("https://example.com/training");
  });

  it("should open news links in a new tab without leaking the referrer window", () => {
    const link: HTMLAnchorElement = fixture.nativeElement.querySelector("a.news-title");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener");
  });

  it("should render the date of items that have one", () => {
    const dates: Element[] = Array.from(fixture.nativeElement.querySelectorAll(".news-date"));
    expect(dates).toHaveLength(1);
    expect(dates[0].textContent!.trim()).toBe(formatDate(items[0].date!, "yyyy-MM-dd", "en-US"));
  });

  it("should not render summaries while showSummary is false", () => {
    expect(fixture.nativeElement.querySelector(".news-summary")).toBeNull();
  });

  it("should render the summary markup when showSummary is set", () => {
    fixture.componentRef.setInput("showSummary", true);
    fixture.detectChanges();

    const summaries: Element[] = Array.from(fixture.nativeElement.querySelectorAll(".news-summary"));
    expect(summaries).toHaveLength(2);
    expect(summaries[0].innerHTML).toContain("Register <b>now</b>.");
  });

  it("should render an empty state when there are no items", () => {
    fixture.componentRef.setInput("items", []);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("ul.news-list")).toBeNull();
    expect(fixture.nativeElement.querySelector(".news-empty")).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain("No news available.");
  });

  it("should render the empty state icon", () => {
    fixture.componentRef.setInput("items", []);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector("mat-icon.news-empty-icon").textContent).toContain("newspaper");
  });
});
