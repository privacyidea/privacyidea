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
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { CertificateHealthEntry, SystemService } from "@services/system/system.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of, Subject, throwError } from "rxjs";
import { CertificateHealthWidgetComponent } from "./certificate-health-widget.component";

function makeResponse(entries: CertificateHealthEntry[]): PiResponse<CertificateHealthEntry[]> {
  return {
    id: 1,
    jsonrpc: "2.0",
    signature: "",
    time: 0,
    version: "",
    versionnumber: "",
    detail: {},
    result: { status: true, value: entries }
  };
}

describe("CertificateHealthWidgetComponent", () => {
  let fixture: ComponentFixture<CertificateHealthWidgetComponent>;
  let component: CertificateHealthWidgetComponent;
  let systemMock: MockSystemService;
  let authMock: MockAuthService;

  const instance: WidgetInstance = { id: "cert-health-1", type: "certificate-health", x: 0, y: 0, cols: 8, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CertificateHealthWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: SystemService, useClass: MockSystemService },
        { provide: AuthService, useClass: MockAuthService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["resolverread"] });

    systemMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    systemMock.getCertificateHealth.mockReturnValue(
      of(
        makeResponse([
          {
            source: "ldap-resolver",
            name: "ldap1",
            host: "ldap.example.com",
            tls_mode: "ldaps",
            subject: "CN=ldap",
            issuer: "CN=ca",
            not_after: "2027-01-01T00:00:00Z",
            days_remaining: 180,
            error: null,
            status: "ok"
          },
          {
            source: "keycloak-resolver",
            name: "kc1",
            host: "kc.example.com",
            tls_mode: "https",
            subject: "CN=kc",
            issuer: "CN=ca",
            not_after: "2026-08-01T00:00:00Z",
            days_remaining: 5,
            error: null,
            status: "critical"
          }
        ])
      )
    );

    fixture = TestBed.createComponent(CertificateHealthWidgetComponent);
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
    expect(CertificateHealthWidgetComponent.type).toBe("certificate-health");
    expect(CertificateHealthWidgetComponent.title).toBeTruthy();
    expect(CertificateHealthWidgetComponent.icon).toBe("verified_user");
  });

  it("should override the static size constraints", () => {
    expect(CertificateHealthWidgetComponent.defaultSize).toEqual({ cols: 8, rows: 5 });
    expect(CertificateHealthWidgetComponent.minSize).toEqual({ cols: 5, rows: 4 });
    expect(CertificateHealthWidgetComponent.maxSize).toEqual({ cols: 16, rows: 10 });
  });

  it("should render a row per certificate entry", () => {
    const rows = fixture.nativeElement.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
  });

  it("should badge status using the shared highlight classes", () => {
    const badges: HTMLElement[] = Array.from(
      fixture.nativeElement.querySelectorAll(".cert-health-table tbody td:last-child span")
    );
    expect(badges[0].className).toBe("highlight-true");
    expect(badges[1].className).toBe("highlight-false");
  });

  it("should link resolver-based entries to the resolver details when resolverread is allowed", () => {
    const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("tbody td a"));
    expect(links.length).toBe(2);
    expect(links[0].getAttribute("href")).toBe(ROUTE_PATHS.USERS_RESOLVERS_DETAILS + "ldap1");
    expect(links[1].getAttribute("href")).toBe(ROUTE_PATHS.USERS_RESOLVERS_DETAILS + "kc1");
  });

  it("should render the name as plain text without resolverread", async () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
    await fixture.whenStable();

    expect(fixture.nativeElement.querySelectorAll("tbody td a").length).toBe(0);
    const nameCell: HTMLElement = fixture.nativeElement.querySelector("tbody tr:first-child td:nth-child(2)");
    expect(nameCell.textContent?.trim()).toBe("ldap1");
  });

  it("should not link entries that do not originate from a resolver", () => {
    systemMock.getCertificateHealth.mockReturnValue(
      of(
        makeResponse([
          {
            source: "privacyidea-server-file",
            name: "/etc/privacyidea/server.pem",
            host: "/etc/privacyidea/server.pem",
            tls_mode: "file",
            subject: "CN=server",
            issuer: "CN=ca",
            not_after: "2027-01-01T00:00:00Z",
            days_remaining: 180,
            error: null,
            status: "ok"
          }
        ])
      )
    );

    const serverFixture = TestBed.createComponent(CertificateHealthWidgetComponent);
    serverFixture.componentRef.setInput("instance", instance);
    serverFixture.detectChanges();

    expect(serverFixture.nativeElement.querySelectorAll("tbody td a").length).toBe(0);
    serverFixture.destroy();
  });

  it("should show a fallback message when there are no certificates to monitor", () => {
    systemMock.getCertificateHealth.mockReturnValue(of(makeResponse([])));

    const emptyFixture = TestBed.createComponent(CertificateHealthWidgetComponent);
    emptyFixture.componentRef.setInput("instance", instance);
    emptyFixture.detectChanges();

    expect(emptyFixture.nativeElement.textContent).toContain("No certificates to monitor.");
    emptyFixture.destroy();
  });

  it("should badge warning and unrecognised statuses with the shared highlight classes", () => {
    systemMock.getCertificateHealth.mockReturnValue(
      of(
        makeResponse([
          {
            source: "privacyidea-server-file",
            name: "warn.pem",
            host: "warn.pem",
            tls_mode: "file",
            subject: "CN=warn",
            issuer: "CN=ca",
            not_after: "2026-09-01T00:00:00Z",
            days_remaining: 20,
            error: null,
            status: "warning"
          },
          {
            source: "privacyidea-server-file",
            name: "weird.pem",
            host: "weird.pem",
            tls_mode: "file",
            subject: "CN=weird",
            issuer: "CN=ca",
            not_after: "2026-09-01T00:00:00Z",
            days_remaining: 20,
            error: null,
            status: "unknown" as CertificateHealthEntry["status"]
          }
        ])
      )
    );

    const badgeFixture = TestBed.createComponent(CertificateHealthWidgetComponent);
    badgeFixture.componentRef.setInput("instance", instance);
    badgeFixture.detectChanges();

    const badges: HTMLElement[] = Array.from(
      badgeFixture.nativeElement.querySelectorAll(".cert-health-table tbody td:last-child span")
    );
    expect(badges[0].className).toBe("highlight-warning");
    expect(badges[1].className).toBe("highlight-disabled");
    badgeFixture.destroy();
  });

  it("should sort entries through each TableSort column accessor", () => {
    for (const column of ["source", "name", "daysRemaining", "status"] as const) {
      component.sort.toggle(column);
      expect(component.sortedEntries().length).toBe(2);
    }
  });

  it("should set the state to loading while the request is still in flight", () => {
    const pending = new Subject<PiResponse<CertificateHealthEntry[]>>();
    systemMock.getCertificateHealth.mockReturnValue(pending.asObservable());
    TestBed.inject(DashboardDataStore).invalidate();

    const loadingFixture = TestBed.createComponent(CertificateHealthWidgetComponent);
    loadingFixture.componentRef.setInput("instance", instance);
    loadingFixture.detectChanges();

    expect(loadingFixture.componentInstance.state()).toBe("loading");
    loadingFixture.destroy();
  });

  it("should set the state to error when the request fails", () => {
    systemMock.getCertificateHealth.mockReturnValue(throwError(() => new Error("boom")));
    TestBed.inject(DashboardDataStore).refreshAll();
    fixture.detectChanges();

    expect(component.state()).toBe("error");
  });

  it("should invalidate the cache and reload on reload()", () => {
    systemMock.getCertificateHealth.mockClear();

    component.reload();

    expect(systemMock.getCertificateHealth).toHaveBeenCalledTimes(1);
  });

  it("should stay in the loading state until the data ref is initialised", () => {
    const initSpy = jest.spyOn(CertificateHealthWidgetComponent.prototype, "ngOnInit").mockReturnValue(undefined);

    const uninitFixture = TestBed.createComponent(CertificateHealthWidgetComponent);
    uninitFixture.componentRef.setInput("instance", instance);
    uninitFixture.detectChanges();

    expect(uninitFixture.componentInstance.state()).toBe("loading");
    uninitFixture.destroy();
    initSpy.mockRestore();
  });
});
