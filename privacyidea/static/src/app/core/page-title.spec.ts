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

import { LiveAnnouncer } from "@angular/cdk/a11y";
import { Component } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { Title } from "@angular/platform-browser";
import { provideRouter, Router, TitleStrategy } from "@angular/router";
import { detailsTitle, newTitle } from "./route-titles";
import { PageTitleStrategy } from "./page-title";

@Component({ selector: "app-test-page", template: "" })
class TestPageComponent {}

describe("PageTitleStrategy", () => {
  let router: Router;
  let title: Title;
  let announcer: LiveAnnouncer;
  let strategy: PageTitleStrategy;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: "tokens", title: "Tokens", component: TestPageComponent },
          { path: "users/realms", title: "Realms", component: TestPageComponent },
          { path: "policies", title: "Policies", component: TestPageComponent },
          {
            path: "policies/details/:name",
            title: detailsTitle("Policies"),
            component: TestPageComponent
          },
          { path: "policies/new", title: newTitle("Policies"), component: TestPageComponent },
          { path: "untitled", component: TestPageComponent },
          {
            path: "group",
            children: [{ path: "child", title: "Child", component: TestPageComponent }]
          }
        ]),
        { provide: TitleStrategy, useExisting: PageTitleStrategy }
      ]
    });
    title = TestBed.inject(Title);
    title.setTitle("privacyIDEA Authentication System");
    announcer = TestBed.inject(LiveAnnouncer);
    jest.spyOn(announcer, "announce").mockResolvedValue();
    strategy = TestBed.inject(PageTitleStrategy);
    router = TestBed.inject(Router);
  });

  it("puts the page's name before the application's in the document title", async () => {
    await router.navigateByUrl("/policies");

    expect(title.getTitle()).toBe("Policies - privacyIDEA Authentication System");
  });

  it("exposes the page's name as the heading", async () => {
    await router.navigateByUrl("/users/realms");

    expect(strategy.heading()).toBe("Realms");
  });

  it("takes the name from the title of the activated child route", async () => {
    await router.navigateByUrl("/group/child");

    expect(strategy.heading()).toBe("Child");
  });

  it("names a new or a record's page after its list", async () => {
    await router.navigateByUrl("/policies/new");
    expect(strategy.heading()).toBe("Policies - New");

    await router.navigateByUrl("/policies/details/hide_welcome");
    expect(strategy.heading()).toBe("Policies - Details");
  });

  it("announces the page when the route changes", async () => {
    await router.navigateByUrl("/tokens");

    expect(announcer.announce).toHaveBeenCalledTimes(1);
    expect(announcer.announce).toHaveBeenCalledWith("Tokens", "polite");
  });

  it("announces each page it moves to", async () => {
    await router.navigateByUrl("/tokens");
    await router.navigateByUrl("/policies");

    expect(announcer.announce).toHaveBeenCalledTimes(2);
    expect(announcer.announce).toHaveBeenLastCalledWith("Policies", "polite");
  });

  it("announces a page again after another page was in between", async () => {
    await router.navigateByUrl("/tokens");
    await router.navigateByUrl("/policies");
    await router.navigateByUrl("/tokens");

    expect(announcer.announce).toHaveBeenCalledTimes(3);
  });

  it("announces nothing when only the query changes", async () => {
    await router.navigateByUrl("/policies");
    await router.navigateByUrl("/policies?filter=a");
    await router.navigateByUrl("/policies?filter=b");
    await router.navigateByUrl("/policies");

    expect(announcer.announce).toHaveBeenCalledTimes(1);
    expect(strategy.heading()).toBe("Policies");
    expect(title.getTitle()).toBe("Policies - privacyIDEA Authentication System");
  });

  it("announces another record of the same list although the heading is the same", async () => {
    await router.navigateByUrl("/policies/details/a");
    await router.navigateByUrl("/policies/details/b");

    expect(announcer.announce).toHaveBeenCalledTimes(2);
  });

  it("falls back to the application's title and announces nothing for a page without a title", async () => {
    await router.navigateByUrl("/untitled");

    expect(title.getTitle()).toBe("privacyIDEA Authentication System");
    expect(strategy.heading()).toBe("");
    expect(announcer.announce).not.toHaveBeenCalled();
  });
});
