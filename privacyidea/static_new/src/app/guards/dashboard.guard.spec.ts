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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { dashboardGuard } from "./dashboard.guard";

describe("dashboardGuard", () => {
  let authService: MockAuthService;
  let router: Router;

  const run = () =>
    TestBed.runInInjectionContext(() =>
      dashboardGuard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot)
    ) as boolean | UrlTree;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: Router, useValue: { parseUrl: jest.fn((url: string) => ({ url }) as unknown as UrlTree) } }
      ]
    });

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    router = TestBed.inject(Router);
  });

  it("allows activation when the dashboard policy is enabled", () => {
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, admin_dashboard: true });

    expect(run()).toBe(true);
    expect(router.parseUrl).not.toHaveBeenCalled();
  });

  it("redirects to the token overview when the dashboard policy is disabled", () => {
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, admin_dashboard: false });

    const result = run();

    expect(router.parseUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS);
    expect((result as unknown as { url: string }).url).toBe(ROUTE_PATHS.TOKENS);
  });
});
