/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { AuditService } from "./audit.service";
import { ContentService } from "../content/content.service";
import { LocalService } from "../local/local.service";
import { TestBed } from "@angular/core/testing";
import { environment } from "../../../environments/environment";
import { provideHttpClient } from "@angular/common/http";
import { signal } from "@angular/core";
import { AuthService } from "../auth/auth.service";
import { FilterValue } from "../../core/models/filter_value";
import { MockAuthService, MockLocalService, MockNotificationService } from "../../../testing/mock-services";

environment.proxyUrl = "/api";

class MockContentService implements Partial<ContentService> {
  routeUrl = signal("/tokens");
}

describe("AuditService (signals & helpers)", () => {
  let auditService: AuditService;
  let content: MockContentService;
  let authService: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        AuditService,
        MockLocalService,
        MockNotificationService
      ]
    });
    auditService = TestBed.inject(AuditService);
    content = TestBed.inject(ContentService) as any;
    authService = TestBed.inject(AuthService) as any;
  });

  it("filterParams ignores unknown keys and wildcard‑wraps allowed ones", () => {
    expect(auditService.filterParams()).toEqual({});

    auditService.auditFilter.set(new FilterValue({ value: "foo: bar action: LOGIN user: alice" }));
    expect(auditService.filterParams()).toEqual({
      action: "*LOGIN*",
      user: "*alice*"
    });
  });

  it("auditResource builds a request when route or tab is audit", () => {
    jest.clearAllMocks();
    const getHeadersMock = jest.spyOn(authService, "getHeaders");

    content.routeUrl.set("/audit");
    auditService.auditResource.reload();
    expect(getHeadersMock).toHaveBeenCalledTimes(1);
  });

  it("auditResource becomes active and derived params update", () => {
    content.routeUrl.set("/audit");
    auditService.auditFilter.set(new FilterValue({ value: "serial: otp123" }));
    auditService.auditResource.reload();

    expect(auditService.auditResource.value()).toBeUndefined();

    expect(auditService.filterParams()).toEqual({ serial: "*otp123*" });
    expect(auditService.pageSize()).toBe(25);
    expect(auditService.pageIndex()).toBe(0);
  });
});
