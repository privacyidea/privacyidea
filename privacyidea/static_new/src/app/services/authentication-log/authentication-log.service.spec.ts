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
import { HttpHeaders, provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuthenticationLogService } from "@services/authentication-log/authentication-log.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";

environment.proxyUrl = "/api";

const emptyPage = () => MockPiResponse.fromValue({ auth_logs: [], count: 0, current: 1, prev: null, next: null });

describe("AuthenticationLogService", () => {
  let service: AuthenticationLogService;
  let authService: MockAuthService;
  let content: MockContentService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: NotificationService, useClass: MockNotificationService },
        AuthenticationLogService
      ]
    });
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    content = TestBed.inject(ContentService) as unknown as MockContentService;
    httpMock = TestBed.inject(HttpTestingController);
    jest.spyOn(authService, "getHeaders").mockReturnValue(new HttpHeaders());
    jest.spyOn(authService, "actionAllowed").mockReturnValue(true);
    // The resource only loads on the authentication-log route, so opt in by default.
    content.routeUrl.set(ROUTE_PATHS.AUTHENTICATION_LOG);
    service = TestBed.inject(AuthenticationLogService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("filterParams keeps known keys verbatim and drops unknown/empty ones", () => {
    expect(service.filterParams()).toEqual({});

    service.authenticationLogFilter.set(
      new FilterValue({ value: "foo: bar username: alice event_type: LOGIN_SUCCESS serial:    " })
    );
    expect(service.filterParams()).toEqual({
      username: "alice",
      event_type: "LOGIN_SUCCESS"
    });
  });

  it("resets pageIndex to 1 (first page) when the filter changes", () => {
    service.pageIndex.set(4);
    service.authenticationLogFilter.set(new FilterValue({ value: "username: bob" }));
    expect(service.pageIndex()).toBe(1);
  });

  it("does not reload when a filter key is added without a value", () => {
    TestBed.tick(); // initial load
    httpMock.match((r) => r.method === "GET").forEach((r) => r.flush(emptyPage()));

    // Adding a key with no value yields the same effective params -> no new request.
    service.authenticationLogFilter.set(new FilterValue({ value: "username: " }));
    TestBed.tick();
    httpMock.expectNone((r) => r.method === "GET");
  });

  it("reloads when a filter value is removed", () => {
    service.authenticationLogFilter.set(new FilterValue({ value: "username: bob" }));
    TestBed.tick();
    httpMock.match((r) => r.method === "GET").forEach((r) => r.flush(emptyPage()));

    // Removing the value (key kept, value gone) changes the effective params -> a fresh request.
    service.authenticationLogFilter.set(new FilterValue({ value: "username: " }));
    TestBed.tick();
    const requests = httpMock.match((r) => r.method === "GET");
    expect(requests.length).toBe(1);
    requests.forEach((r) => r.flush(emptyPage()));
  });

  it("builds a GET request with 1-based page, sort and filter params", async () => {
    service.authenticationLogFilter.set(new FilterValue({ value: "serial: PISP0001" }));
    service.authenticationLogResource.reload();
    TestBed.tick();

    const req = httpMock.expectOne((r) => r.url.includes("/authenticationlog/"));
    expect(req.request.method).toBe("GET");
    expect(req.request.params.get("page")).toBe("1");
    expect(req.request.params.get("page_size")).toBe("15");
    expect(req.request.params.get("sort_column")).toBe("timestamp");
    expect(req.request.params.get("sort_order")).toBe("desc");
    expect(req.request.params.get("case_insensitive")).toBe("true");
    expect(req.request.params.get("serial")).toBe("PISP0001");

    req.flush(emptyPage());
    await Promise.resolve();
    TestBed.tick();
  });

  it("sends the 1-based pageIndex verbatim as the API page", async () => {
    service.pageIndex.set(3);
    service.authenticationLogResource.reload();
    TestBed.tick();

    const req = httpMock.expectOne((r) => r.url.includes("/authenticationlog/"));
    expect(req.request.params.get("page")).toBe("3");
    req.flush(emptyPage());
    await Promise.resolve();
    TestBed.tick();
  });

  it("includes start/end only when set", async () => {
    service.start.set("2026-01-01T00:00:00+00:00");
    service.end.set("2026-06-01T00:00:00+00:00");
    service.authenticationLogResource.reload();
    TestBed.tick();

    const req = httpMock.expectOne((r) => r.url.includes("/authenticationlog/"));
    expect(req.request.params.get("start")).toBe("2026-01-01T00:00:00+00:00");
    expect(req.request.params.get("end")).toBe("2026-06-01T00:00:00+00:00");
    req.flush(emptyPage());
    await Promise.resolve();
    TestBed.tick();
  });

  it("does not load off the authentication-log route", () => {
    content.routeUrl.set(ROUTE_PATHS.AUDIT);
    service.authenticationLogResource.reload();
    TestBed.tick();
    httpMock.expectNone((r) => r.url.includes("/authenticationlog/"));
  });

  it("does not load without the read right", () => {
    (authService.actionAllowed as jest.Mock).mockReturnValue(false);
    service.authenticationLogResource.reload();
    TestBed.tick();
    httpMock.expectNone((r) => r.url.includes("/authenticationlog/"));
  });
});
