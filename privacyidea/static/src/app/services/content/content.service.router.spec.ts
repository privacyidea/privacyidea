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
import { Component } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ContentService } from "./content.service";

@Component({ template: "" })
class DummyComponent {}

// Runs the navigation helpers through the real router, so the URLs they produce are parsed the way the app
// parses them.
const settle = () => new Promise((resolve) => setTimeout(resolve));

describe("ContentService with the real router", () => {
  let service: ContentService;
  let router: Router;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        ContentService,
        provideRouter([
          { path: "users/details/:username", component: DummyComponent },
          { path: "tokens/details/:serial", component: DummyComponent },
          { path: "containers/details/:serial", component: DummyComponent },
          { path: "**", component: DummyComponent }
        ])
      ]
    });
    service = TestBed.inject(ContentService);
    router = TestBed.inject(Router);
    await router.navigateByUrl("/tokens");
  });

  it.each(["alice", "a(b)@c", "a b/ü;x", "A#1", "100%"])("userSelected round-trips the login %s", async (login) => {
    service.userSelected(login, "r 1&x");
    await settle();
    expect(service.detailsUser()).toEqual({ username: login, realm: "r 1&x" });
  });

  it.each(["SER1", "a(b)", "A#1", "A/B 1", "100%"])("tokenSelected round-trips the serial %s", async (serial) => {
    service.tokenSelected(serial);
    await settle();
    expect(service.tokenSerial()).toBe(serial);
  });

  it.each(["C1", "a(b)", "A#1", "A/B 1"])("navigateContainerDetails round-trips the serial %s", async (serial) => {
    service.navigateContainerDetails(serial);
    await settle();
    expect(service.containerSerial()).toBe(serial);
  });

  // Every details route that takes its key as the last path segment, whichever page opens it.
  const detailsPaths = Object.entries(ROUTE_PATHS)
    .filter(([name, path]) => name.endsWith("_DETAILS") && path.endsWith("/"))
    .map(([name, path]) => [name, path] as const);

  it("finds details routes to check", () => {
    expect(detailsPaths.length).toBeGreaterThan(10);
  });

  describe.each(detailsPaths)("%s", (_name, path) => {
    it.each(["plain", "a(b)", "A#1", "a?b", "a/b", "a;x=1", "100%", "a b/ü"])(
      "opens the details page of %s with the array form of router.navigate",
      async (key) => {
        await router.navigate([path, key]);
        const segments = router.parseUrl(router.url).root.children["primary"].segments;
        expect(segments[segments.length - 1].path).toBe(key);
        expect(router.parseUrl(router.url).fragment).toBeNull();
        expect(router.parseUrl(router.url).queryParams).toEqual({});
      }
    );
  });
});
