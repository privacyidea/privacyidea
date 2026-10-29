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

import { Route, Routes } from "@angular/router";
import { routes as appRoutes } from "./app.routes";
import { routes as adminRoutes } from "./admin.routes";
import { routes as selfServiceRoutes } from "./self-service.routes";
import { detailsTitle, newTitle, PAGE_NAMES } from "./core/route-titles";
import { ALL_PAGES } from "../../playwright-e2e/support/routes";

// Every route that draws a page, with the path it is reached by and the title it carries. A route that only groups
// its children, redirects or matches anything else draws no page of its own.
function pagesOf(routes: Routes, parent = ""): { path: string; route: Route }[] {
  return routes.flatMap((route) => {
    const path = [parent, route.path].filter(Boolean).join("/");
    const own = route.component || route.loadComponent ? [{ path: path || "/", route }] : [];
    return [...own, ...pagesOf(route.children ?? [], path)];
  });
}

describe("route titles", () => {
  // The admin and self-service routes are lazy children of the layout route, so they are walked on their own.
  const trees: [string, Routes][] = [
    ["app", appRoutes.filter((route) => route.path === "login")],
    ["admin", adminRoutes],
    ["self-service", selfServiceRoutes]
  ];

  it.each(trees)("gives every page of the %s routes a title", (_name, routes) => {
    const pages = pagesOf(routes);
    expect(pages.length).toBeGreaterThan(0);
    const untitled = pages.filter(({ route }) => typeof route.title !== "string" || route.title.trim() === "");
    expect(untitled.map(({ path }) => path)).toEqual([]);
  });

  it.each(trees)("gives every page of the %s routes a title of its own", (_name, routes) => {
    const pages = pagesOf(routes);
    const duplicates = pages.filter(
      ({ route }, i) => pages.findIndex((other) => other.route.title === route.title) !== i
    );
    expect(duplicates.map(({ path, route }) => `${path}: ${String(route.title)}`)).toEqual([]);
  });

  it("has the e2e suite visit every admin page that needs no record", () => {
    const visited = new Set(ALL_PAGES.map(({ path }) => path));
    const missing = pagesOf(adminRoutes)
      .map(({ path }) => path)
      .filter((path) => !path.includes(":") && !visited.has(path));
    expect(missing).toEqual([]);
  });

  it("walks the nested routes", () => {
    const paths = pagesOf(adminRoutes).map(({ path }) => path);

    expect(paths).toContain("policies/api-clients/details/:id");
    expect(paths).toContain("containers/templates/create");
  });

  it("builds the title of a new page and of a record's page from the name of its list", () => {
    expect(newTitle(PAGE_NAMES.policies)).toBe("Policies - new");
    expect(detailsTitle(PAGE_NAMES.smtp)).toBe("SMTP servers - details");
  });
});
