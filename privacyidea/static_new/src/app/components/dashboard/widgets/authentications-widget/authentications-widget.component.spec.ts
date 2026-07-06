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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { Audit, AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { MockAuditService } from "@testing/mock-services/mock-audit-service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of, Subject } from "rxjs";
import { AuthenticationsWidgetComponent } from "./authentications-widget.component";

function makeAuditResponse(count: number, auditdata: object[] = []) {
  return {
    id: 1,
    jsonrpc: "2.0",
    signature: "",
    time: 0,
    version: "",
    versionnumber: "",
    detail: {},
    result: {
      status: true,
      value: { count, current: 1, auditcolumns: [], auditdata }
    }
  };
}

describe("AuthenticationsWidgetComponent", () => {
  let fixture: ComponentFixture<AuthenticationsWidgetComponent>;
  let component: AuthenticationsWidgetComponent;
  let authMock: MockAuthService;
  let auditMock: MockAuditService;

  const instance: WidgetInstance = {
    id: "authentications-1",
    type: "authentications",
    x: 0,
    y: 0,
    cols: 6,
    rows: 5
  };

  function stubAuditResponses(successCount = 42, failCount = 7, auditdata: object[] = []): void {
    auditMock.fetchAuditPage.mockImplementation((params: Record<string, string | number>) =>
      params["success"] === "1" ? of(makeAuditResponse(successCount)) : of(makeAuditResponse(failCount, auditdata))
    );
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuthenticationsWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: ContentService, useClass: MockContentService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["auditlog"] });

    auditMock = TestBed.inject(AuditService) as unknown as MockAuditService;
    stubAuditResponses();

    fixture = TestBed.createComponent(AuthenticationsWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    expect(AuthenticationsWidgetComponent.type).toBe("authentications");
    expect(AuthenticationsWidgetComponent.title).toBeTruthy();
    expect(AuthenticationsWidgetComponent.icon).toBe("receipt_long");
  });

  it("should override the static size constraints", () => {
    expect(AuthenticationsWidgetComponent.defaultSize).toEqual({ cols: 8, rows: 6 });
    expect(AuthenticationsWidgetComponent.minSize).toEqual({ cols: 5, rows: 5 });
    expect(AuthenticationsWidgetComponent.maxSize).toEqual({ cols: 10, rows: 8 });
  });

  it("should render success and fail counts when right is granted", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("42");
    expect(text).toContain("7");
  });

  it("should render the subtitle and row labels", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("Authentications in the last 24 hours");
    expect(text).toContain("Success");
    expect(text).toContain("Failure");
    expect(text).toContain("Users / Tokens with Failures");
  });

  it("should render aggregated failed users with fail counts", async () => {
    const auditdata = [
      { user: "alice", realm: "testrealm", date: "2026-01-02T10:00:00" },
      { user: "alice", realm: "testrealm", date: "2026-01-02T11:00:00" },
      { user: "bob", realm: "testrealm", date: "2026-01-02T09:00:00" }
    ];
    stubAuditResponses(10, 3, auditdata);

    const fixture2 = TestBed.createComponent(AuthenticationsWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    const text = fixture2.nativeElement.textContent;
    expect(text).toContain("alice@testrealm[2]");
    expect(text).toContain("bob@testrealm[1]");
    fixture2.destroy();
  });

  it("should render serials for failed entries without a user", async () => {
    const auditdata = [{ serial: "TOTP001234" }, { serial: "HOTP005678" }];
    stubAuditResponses(5, 2, auditdata);

    const fixture2 = TestBed.createComponent(AuthenticationsWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    const text = fixture2.nativeElement.textContent;
    expect(text).toContain("TOTP001234");
    expect(text).toContain("HOTP005678");
    fixture2.destroy();
  });

  it("should render nothing when auditlog right is missing", () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });

    const fixture2 = TestBed.createComponent(AuthenticationsWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("table")).toBeNull();
    fixture2.destroy();
  });

  it("should set the state to loading while the requests are still in flight", () => {
    TestBed.inject(DashboardDataStore).invalidate();
    auditMock.fetchAuditPage.mockImplementation(() => new Subject<MockPiResponse<Audit>>().asObservable());

    const fixture2 = TestBed.createComponent(AuthenticationsWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.componentInstance.state()).toBe("loading");
    fixture2.destroy();
  });

  it("should set the state to error when a request fails", () => {
    TestBed.inject(DashboardDataStore).invalidate();
    const subject = new Subject<MockPiResponse<Audit>>();
    auditMock.fetchAuditPage.mockImplementation(() => subject.asObservable());

    const fixture2 = TestBed.createComponent(AuthenticationsWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();
    subject.error(new Error("boom"));
    fixture2.detectChanges();

    expect(fixture2.componentInstance.state()).toBe("error");
    fixture2.destroy();
  });

  it("should invalidate the cache and reload on reload()", () => {
    auditMock.fetchAuditPage.mockClear();

    component.reload();

    expect(auditMock.fetchAuditPage).toHaveBeenCalledTimes(2);
  });
});
