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
import { Component, provideZonelessChangeDetection } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { provideRouter, Routes } from "@angular/router";
import { RouterTestingHarness } from "@angular/router/testing";
import { LayoutComponent } from "@components/layout/layout.component";
import { AuthService } from "@services/auth/auth.service";
import { DashboardLayoutService } from "@services/dashboard/dashboard-layout.service";
import { UserSettingsService } from "@services/user-settings/user-settings.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockUserSettingsService } from "@testing/mock-services/mock-user-settings-service";
import { routerFeatures } from "./app.config";
import { routes } from "./app.routes";

@Component({ template: "" })
class StubComponent {}

describe("session services of the layout route", () => {
  const layoutRoute = routes.find((route) => route.component === LayoutComponent);

  it("provides the dashboard layout in the providers of the layout route", () => {
    expect(layoutRoute?.providers).toContain(DashboardLayoutService);
  });

  it("creates the services of the layout route anew after leaving it for the login page", async () => {
    // The real layout route, with its components and guards replaced by stubs: the providers and the router
    // features are the ones the application uses.
    const testRoutes: Routes = [
      { path: "login", component: StubComponent },
      {
        path: "",
        component: StubComponent,
        providers: (layoutRoute?.providers ?? []).filter((provider) => provider === DashboardLayoutService),
        children: [{ path: "dashboard", component: StubComponent }]
      }
    ];
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideRouter(testRoutes, ...routerFeatures),
        { provide: AuthService, useClass: MockAuthService },
        { provide: UserSettingsService, useClass: MockUserSettingsService }
      ]
    });
    const harness = await RouterTestingHarness.create();

    await harness.navigateByUrl("/dashboard");
    const first = harness.routeDebugElement?.injector.get(DashboardLayoutService);
    await harness.navigateByUrl("/login");
    await harness.navigateByUrl("/dashboard");
    const second = harness.routeDebugElement?.injector.get(DashboardLayoutService);

    expect(first).toBeInstanceOf(DashboardLayoutService);
    expect(second).toBeInstanceOf(DashboardLayoutService);
    expect(second).not.toBe(first);
  });
});
