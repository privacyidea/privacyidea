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
import { FilterValue } from "@core/models/filter_value/filter_value";
import { environment } from "@env/environment";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import {
  MockContentService,
  MockDialogService,
  MockLocalService,
  MockNotificationService,
  MockPiResponse
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { toFilterDisplay } from "@utils/date-format.utils";

environment.proxyUrl = "/api";

describe("AuditService (signals & helpers)", () => {
  let auditService: AuditService;
  let content: MockContentService;
  let authService: MockAuthService;
  let dialogService: MockDialogService;
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
        { provide: DialogService, useClass: MockDialogService },
        AuditService,
        MockLocalService
      ]
    });
    auditService = TestBed.inject(AuditService);
    content = TestBed.inject(ContentService) as unknown as MockContentService;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    // The audit log is only requested by someone who may read it.
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["auditlog"] });
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    httpMock = TestBed.inject(HttpTestingController);
  });

  it("filterParams ignores unknown keys and wildcard‑wraps allowed ones", () => {
    expect(auditService.filterParams()).toEqual({});

    auditService.activeFilter.set(new FilterValue({ value: "foo: bar action: LOGIN user: alice" }));
    expect(auditService.filterParams()).toEqual({
      action: "*LOGIN*",
      user: "*alice*"
    });
  });

  it("filterParams sends a day filter on the entry date", () => {
    auditService.activeFilter.set(new FilterValue({ value: "date: 2026-09-25" }));
    expect(auditService.filterParams()).toEqual({ date: "*2026-09-25*" });
  });

  it("auditResource builds a request when route or tab is audit", async () => {
    jest.clearAllMocks();
    const getHeadersMock = jest.spyOn(authService, "getHeaders");

    content.routeUrl.set("/logs/audit");
    auditService.auditResource.reload();
    expect(getHeadersMock).toHaveBeenCalledTimes(1);

    TestBed.tick();
    const req = httpMock.expectOne((req) => req.url.includes("/audit"));
    const response = MockPiResponse.fromValue({
      auditcolumns: [],
      auditdata: [{ action: "GET /token" }, { action: "GET /audit" }],
      count: 2,
      current: 1,
      next: 1,
      prev: 1
    });
    req.flush(response);
    await Promise.resolve();
    TestBed.tick();
  });

  it("auditResource does not request the audit log without auditlog", () => {
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
    content.routeUrl.set("/logs/audit");
    TestBed.tick();

    httpMock.expectNone((req) => req.url.includes("/audit"));
  });

  it("auditResource becomes active and derived params update", () => {
    content.routeUrl.set("/logs/audit");
    auditService.activeFilter.set(new FilterValue({ value: "serial: otp123" }));
    auditService.auditResource.reload();

    expect(auditService.auditResource.value()).toBeUndefined();

    expect(auditService.filterParams()).toEqual({ serial: "*otp123*" });
    expect(auditService.pageSize()).toBe(25);
    expect(auditService.pageIndex()).toBe(1);
  });

  it("resets pageIndex to 1 when activeFilter change", () => {
    auditService.pageIndex.set(3);
    auditService.activeFilter.set(new FilterValue({ value: "user: bob success: true" }));

    expect(auditService.pageIndex()).toBe(1);
  });

  it("should not include empty filter values in filterParams", () => {
    auditService.activeFilter.set(
      new FilterValue({ value: "action: authentication: ACCEPT serial: \"   \" container_serial: *" })
    );

    const params = auditService.filterParams();
    expect(params).not.toHaveProperty("action");
    expect(params).toHaveProperty("authentication", "*ACCEPT*");
    expect(params).not.toHaveProperty("serial");
    expect(params).not.toHaveProperty("container_serial");
  });

  it("downloadCSV triggers a GET request with correct params and headers after dialog confirmation", async () => {
    const getHeadersMock = jest.spyOn(authService, "getHeaders").mockReturnValue(new HttpHeaders());
    auditService.activeFilter.set(new FilterValue({ value: "action: LOGIN" }));

    auditService.downloadCSV();

    expect(dialogService.openDialog).toHaveBeenCalled();
    const dialogRef = (dialogService.openDialog as jest.Mock).mock.results[0].value;
    dialogRef.close(true);
    await Promise.resolve();

    const req = httpMock.expectOne((req) => req.url.endsWith("/audit/audit.csv"));
    expect(req.request.method).toBe("GET");
    expect(req.request.params.get("action")).toBe("*LOGIN*");
    expect(getHeadersMock).toHaveBeenCalled();
    req.flush("test data");
  });

  it("sends the startdate interval to search and download", async () => {
    const fromIso = "2026-09-24T22:00:00.000Z";
    const toIso = "2026-09-25T21:59:59.000Z";
    // The range lives in the startdate chip, written the way the range picker writes it.
    auditService.activeFilter.set(
      new FilterValue({ value: "action: LOGIN" }).addEntry(
        "startdate",
        `${toFilterDisplay(fromIso)}/${toFilterDisplay(toIso)}`
      )
    );

    content.routeUrl.set("/logs/audit");
    TestBed.tick();
    const searchReq = httpMock.expectOne((req) => req.url.endsWith("/audit/"));
    expect(searchReq.request.params.get("startdate")).toBe(`${fromIso}/${toIso}`);
    expect(searchReq.request.params.has("start_time")).toBe(false);
    expect(searchReq.request.params.has("end_time")).toBe(false);
    expect(searchReq.request.params.get("action")).toBe("*LOGIN*");
    searchReq.flush(MockPiResponse.fromValue({ auditcolumns: [], auditdata: [], count: 0, current: 1 }));

    auditService.downloadCSV();
    const dialogRef = (dialogService.openDialog as jest.Mock).mock.results[0].value;
    dialogRef.close(true);
    await Promise.resolve();

    const downloadReq = httpMock.expectOne((req) => req.url.endsWith("/audit/audit.csv"));
    expect(downloadReq.request.params.get("startdate")).toBe(`${fromIso}/${toIso}`);
    expect(downloadReq.request.params.has("start_time")).toBe(false);
    expect(downloadReq.request.params.has("end_time")).toBe(false);
    expect(downloadReq.request.params.get("action")).toBe("*LOGIN*");
    downloadReq.flush("test data");

    // An open end stays empty.
    auditService.activeFilter.set(new FilterValue().addEntry("startdate", `${toFilterDisplay(fromIso)}/`));
    TestBed.tick();
    const openEndReq = httpMock.expectOne((req) => req.url.endsWith("/audit/"));
    expect(openEndReq.request.params.get("startdate")).toBe(`${fromIso}/`);
    expect(auditService.timestampTo()).toBeNull();
    openEndReq.flush(MockPiResponse.fromValue({ auditcolumns: [], auditdata: [], count: 0, current: 1 }));
  });

  it("a plain startdate text filter is no time range", () => {
    auditService.activeFilter.set(new FilterValue({ value: "startdate: 2026-11-05" }));
    expect(auditService.timestampFrom()).toBeNull();
    expect(auditService.timestampTo()).toBeNull();

    content.routeUrl.set("/logs/audit");
    TestBed.tick();
    const searchReq = httpMock.expectOne((req) => req.url.endsWith("/audit/"));
    expect(searchReq.request.params.get("startdate")).toBe("*2026-11-05*");
    searchReq.flush(MockPiResponse.fromValue({ auditcolumns: [], auditdata: [], count: 0, current: 1 }));
  });

  it("sends a typed date interval without wildcards", () => {
    auditService.activeFilter.set(new FilterValue({ value: 'date: "2026-11-05 00:00:00 +01:00/"' }));
    content.routeUrl.set("/logs/audit");
    TestBed.tick();
    const searchReq = httpMock.expectOne((req) => req.url.endsWith("/audit/"));
    expect(searchReq.request.params.get("date")).toBe("2026-11-04T23:00:00.000Z/");
    searchReq.flush(MockPiResponse.fromValue({ auditcolumns: [], auditdata: [], count: 0, current: 1 }));
  });

  describe("typed bounds without an offset", () => {
    // Expectations are built with the local Date constructor, so they hold in any zone. In a zone away from UTC
    // (as on a developer machine) a bound read as UTC instead of local fails them.
    // The interval the audit request carries for a typed chip value.
    const sentInterval = (key: string, value: string): string | null => {
      auditService.activeFilter.set(new FilterValue().addEntry(key, value));
      content.routeUrl.set("/logs/audit");
      TestBed.tick();
      const req = httpMock.expectOne((r) => r.url.endsWith("/audit/"));
      const sent: string | null = req.request.params.get(key);
      req.flush(MockPiResponse.fromValue({ auditcolumns: [], auditdata: [], count: 0, current: 1 }));
      return sent;
    };

    it.each(["startdate", "date"])("%s: a date and time is the viewer's local time", (key) => {
      expect(sentInterval(key, "2026-11-05 10:00:00/")).toBe(`${new Date(2026, 10, 5, 10, 0, 0, 0).toISOString()}/`);
    });

    it.each(["startdate", "date"])("%s: a date alone is local midnight, not UTC midnight", (key) => {
      expect(sentInterval(key, "2026-11-05/")).toBe(`${new Date(2026, 10, 5, 0, 0, 0, 0).toISOString()}/`);
    });

    it.each(["startdate", "date"])("%s: a bound with Z is sent as given", (key) => {
      expect(sentInterval(key, "/2026-11-05T10:00:00Z")).toBe("/2026-11-05T10:00:00.000Z");
    });

    it.each(["startdate", "date"])("%s: an end that is only a date includes that whole local day", (key) => {
      expect(sentInterval(key, "2026-11-04/2026-11-05")).toBe(
        `${new Date(2026, 10, 4, 0, 0, 0, 0).toISOString()}/${new Date(2026, 10, 5, 23, 59, 59, 0).toISOString()}`
      );
    });

    it.each(["startdate", "date"])("%s: an end that is only a month runs to the end of its last local day", (key) => {
      expect(sentInterval(key, "/2026-11")).toBe(`/${new Date(2026, 10, 30, 23, 59, 59, 0).toISOString()}`);
    });

    it.each(["startdate", "date"])("%s: an end with a time is that time", (key) => {
      expect(sentInterval(key, "/2026-11-05 13:00:00")).toBe(`/${new Date(2026, 10, 5, 13, 0, 0, 0).toISOString()}`);
    });

    it("date: an unparsable edit keeps the previous bound", () => {
      const localMidnight: string = new Date(2026, 10, 5, 0, 0, 0, 0).toISOString();
      expect(sentInterval("date", "2026-11-05/")).toBe(`${localMidnight}/`);
      expect(sentInterval("date", "2026-11-05 1x/")).toBe(`${localMidnight}/`);
    });
  });

  it("downloadCSV does not trigger a GET request if dialog is cancelled", () => {
    auditService.downloadCSV();

    expect(dialogService.openDialog).toHaveBeenCalled();
    const dialogRef = (dialogService.openDialog as jest.Mock).mock.results[0].value;
    dialogRef.close(false);

    httpMock.expectNone((req) => req.url.endsWith("/audit/audit.csv"));
    expect(auditService.isDownloading()).toBe(false);
  });

  it("should set isDownloading to true while downloading and false after completion", async () => {
    auditService.downloadCSV();
    const dialogRef = (dialogService.openDialog as jest.Mock).mock.results[0].value;
    dialogRef.close(true);
    await Promise.resolve();

    expect(auditService.isDownloading()).toBe(true);
    const req = httpMock.expectOne((req) => req.url.endsWith("/audit/audit.csv"));
    req.flush("test data");
    expect(auditService.isDownloading()).toBe(false);
  });

  it("should set isDownloading to false on error", async () => {
    auditService.downloadCSV();
    const dialogRef = (dialogService.openDialog as jest.Mock).mock.results[0].value;
    dialogRef.close(true);
    await Promise.resolve();

    expect(auditService.isDownloading()).toBe(true);
    const req = httpMock.expectOne((req) => req.url.endsWith("/audit/audit.csv"));
    req.error(new ErrorEvent("error"));
    expect(auditService.isDownloading()).toBe(false);
  });
});
