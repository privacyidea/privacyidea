import { AuditService } from "./audit.service";
import { ContentService } from "../content/content.service";
import { LocalService } from "../local/local.service";
import { TestBed } from "@angular/core/testing";
import { environment } from "../../../environments/environment";
import { provideHttpClient } from "@angular/common/http";
import { signal } from "@angular/core";

environment.proxyUrl = "/api";

class MockLocalService implements Partial<LocalService> {
  getHeaders = jest.fn().mockReturnValue({ Authorization: "Bearer x" });
}

class MockContentService implements Partial<ContentService> {
  routeUrl = signal("/tokens");
}

describe("AuditService (signals & helpers)", () => {
  let auditService: AuditService;
  let content: MockContentService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: LocalService, useClass: MockLocalService },
        { provide: ContentService, useClass: MockContentService },
        AuditService
      ]
    });
    auditService = TestBed.inject(AuditService);
    content = TestBed.inject(ContentService) as any;
  });

  it("filterParams ignores unknown keys and wildcard‑wraps allowed ones", () => {
    expect(auditService.filterParams()).toEqual({});

    auditService.auditFilter.set({
      action: "LOGIN",
      foo: "bar",
      user: "alice"
    });
    expect(auditService.filterParams()).toEqual({
      action: "*LOGIN*",
      user: "*alice*"
    });
  });

  it("auditResource builds a request when route or tab is audit", () => {
    const local = TestBed.inject(LocalService) as any;
    jest.clearAllMocks();

    content.routeUrl.set("/audit");
    auditService.auditResource.reload();
    expect(local.getHeaders).toHaveBeenCalledTimes(1);
  });

  it("auditResource becomes active and derived params update", () => {
    content.routeUrl.set("/audit");
    auditService.auditFilter.set({ serial: "otp123" });

    auditService.auditResource.reload();

    expect(auditService.auditResource.value()).toBeUndefined();

    expect(auditService.filterParams()).toEqual({ serial: "*otp123*" });
    expect(auditService.pageSize()).toBe(10);
    expect(auditService.pageIndex()).toBe(0);
  });
});
