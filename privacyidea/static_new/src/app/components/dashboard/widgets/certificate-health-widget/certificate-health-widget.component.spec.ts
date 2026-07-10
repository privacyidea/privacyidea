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
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { CertificateHealthEntry, SystemService } from "@services/system/system.service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of } from "rxjs";
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

  const instance: WidgetInstance = { id: "cert-health-1", type: "certificate-health", x: 0, y: 0, cols: 8, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CertificateHealthWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

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

  it("should show a fallback message when there are no certificates to monitor", () => {
    systemMock.getCertificateHealth.mockReturnValue(of(makeResponse([])));

    const emptyFixture = TestBed.createComponent(CertificateHealthWidgetComponent);
    emptyFixture.componentRef.setInput("instance", instance);
    emptyFixture.detectChanges();

    expect(emptyFixture.nativeElement.textContent).toContain("No certificates to monitor.");
    emptyFixture.destroy();
  });
});
