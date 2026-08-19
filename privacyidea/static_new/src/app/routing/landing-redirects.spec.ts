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
import { ActivatedRouteSnapshot } from "@angular/router";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { firstAllowedRedirect, logsLandingRedirect } from "./landing-redirects";

describe("logsLandingRedirect", () => {
  let authService: MockAuthService;

  const run = () =>
    TestBed.runInInjectionContext(() => logsLandingRedirect({} as ActivatedRouteSnapshot, {} as never)) as string;

  const allow = (...actions: string[]) =>
    (authService.actionAllowed as jest.Mock).mockImplementation((action: string) => actions.includes(action));

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService }
      ]
    });
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  it("redirects to audit when the audit log is allowed", () => {
    allow("auditlog", "authentication_log_read", "clienttype");
    expect(run()).toBe("audit");
  });

  it("redirects to the authentication log when audit is not allowed", () => {
    allow("authentication_log_read", "clienttype");
    expect(run()).toBe("authentication-log");
  });

  it("redirects to known clients when only client access is allowed", () => {
    allow("clienttype");
    expect(run()).toBe("clients");
  });

  it("falls back to audit when no log action is allowed", () => {
    allow();
    expect(run()).toBe("audit");
  });

  it("firstAllowedRedirect returns the first allowed candidate, else the fallback", () => {
    const redirect = firstAllowedRedirect(
      [
        ["auditlog", "first"],
        ["clienttype", "second"]
      ],
      "none"
    );
    const runWith = () => TestBed.runInInjectionContext(() => redirect({} as ActivatedRouteSnapshot, {} as never));

    allow("clienttype");
    expect(runWith()).toBe("second");

    allow("auditlog", "clienttype");
    expect(runWith()).toBe("first");

    allow();
    expect(runWith()).toBe("none");
  });
});
