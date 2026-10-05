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
import { TestBed } from "@angular/core/testing";
import { Title } from "@angular/platform-browser";
import { RouterStateSnapshot } from "@angular/router";
import { pageTitleFor, PageTitleStrategy } from "./page-title";

describe("pageTitleFor", () => {
  it("names a list page", () => {
    expect(pageTitleFor("/policies")).toBe("Policies");
    expect(pageTitleFor("/policies/conditional-access")).toBe("Conditional access policies");
  });

  it("ignores the query, the fragment and a trailing slash", () => {
    expect(pageTitleFor("/tokens/?page=2#top")).toBe("Tokens");
  });

  it("names a new or created record after its list", () => {
    expect(pageTitleFor("/policies/new")).toBe("Policies – new");
    expect(pageTitleFor("/containers/create")).toBe("Containers – new");
  });

  it("names a record's page after its list", () => {
    expect(pageTitleFor("/tokens/details/HOTP0001")).toBe("Tokens – details");
    expect(pageTitleFor("/external-services/smtp/details/mail")).toBe("SMTP servers – details");
  });

  it("takes the first keyword segment after a page, so a record may be named like a keyword", () => {
    expect(pageTitleFor("/policies/details/new")).toBe("Policies – details");
    expect(pageTitleFor("/tokens/details/details")).toBe("Tokens – details");
    expect(pageTitleFor("/containers/templates/details/create")).toBe("Container templates – details");
  });

  it("has no name for a path no page is known by", () => {
    expect(pageTitleFor("/nowhere")).toBeUndefined();
    expect(pageTitleFor("/nowhere/new")).toBeUndefined();
  });
});

describe("PageTitleStrategy", () => {
  let strategy: PageTitleStrategy;
  let title: Title;
  let announcer: LiveAnnouncer;
  const snapshot = (url: string) => ({ url }) as RouterStateSnapshot;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    title = TestBed.inject(Title);
    title.setTitle("privacyIDEA Authentication System");
    announcer = TestBed.inject(LiveAnnouncer);
    jest.spyOn(announcer, "announce").mockResolvedValue();
    strategy = TestBed.inject(PageTitleStrategy);
  });

  it("puts the page's name before the application's in the document title", () => {
    strategy.updateTitle(snapshot("/policies"));

    expect(title.getTitle()).toBe("Policies – privacyIDEA Authentication System");
  });

  it("exposes the page's name as the heading", () => {
    strategy.updateTitle(snapshot("/users/realms"));

    expect(strategy.heading()).toBe("Realms");
  });

  it("announces the page when the route changes", () => {
    strategy.updateTitle(snapshot("/tokens"));

    expect(announcer.announce).toHaveBeenCalledWith("Tokens", "polite");
  });

  it("falls back to the application's title and announces nothing for an unknown path", () => {
    strategy.updateTitle(snapshot("/nowhere"));

    expect(title.getTitle()).toBe("privacyIDEA Authentication System");
    expect(strategy.heading()).toBe("");
    expect(announcer.announce).not.toHaveBeenCalled();
  });
});
