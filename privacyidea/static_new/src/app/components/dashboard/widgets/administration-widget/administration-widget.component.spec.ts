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
import { DASHBOARD_COLUMNS, DashboardWidget, WidgetInstance } from "@models/dashboard";
import { Audit, AuditData, AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { MockAuditService } from "@testing/mock-services/mock-audit-service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of } from "rxjs";
import { AdministrationWidgetComponent } from "./administration-widget.component";

const ADMIN_AREAS = ["system", "resolver", "realm", "policy", "event"];

describe("AdministrationWidgetComponent", () => {
  let fixture: ComponentFixture<AdministrationWidgetComponent>;
  let component: AdministrationWidgetComponent;
  let auditMock: MockAuditService;
  let authService: MockAuthService;

  const instance: WidgetInstance = { id: "admin-1", type: "administration", x: 0, y: 0, cols: 10, rows: 5 };

  function stubAreas(dataPerArea: AuditData[][]): void {
    auditMock.fetchAuditPage.mockImplementation((params: Record<string, string | number>) => {
      const action = String(params["action"] ?? "");
      const idx = ADMIN_AREAS.findIndex((area) => action === `POST /${area}*`);
      const auditdata = idx >= 0 ? (dataPerArea[idx] ?? []) : [];
      return of(MockPiResponse.fromValue<Audit>({ auditcolumns: [], auditdata, count: 0, current: 1 }));
    });
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdministrationWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: AuditService, useClass: MockAuditService }
      ]
    }).compileComponents();

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["auditlog"] });

    auditMock = TestBed.inject(AuditService) as unknown as MockAuditService;
    stubAreas([[], [], [], [], []]);

    fixture = TestBed.createComponent(AdministrationWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
  });

  it("should create", () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    fixture.detectChanges();
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    fixture.detectChanges();
    expect(AdministrationWidgetComponent.type).toBe("administration");
    expect(AdministrationWidgetComponent.title).toBeTruthy();
    expect(AdministrationWidgetComponent.icon).toBe("supervised_user_circle");
  });

  it("should override the static size constraints", () => {
    fixture.detectChanges();
    expect(AdministrationWidgetComponent.defaultSize).toEqual({ cols: 10, rows: 6 });
    expect(AdministrationWidgetComponent.minSize).toEqual({ cols: 7, rows: 4 });
    expect(AdministrationWidgetComponent.maxSize).toEqual({ cols: DASHBOARD_COLUMNS, rows: 8 });
  });

  it("should render audit rows in the table", () => {
    const entries: AuditData[] = [
      { number: 1, date: "2026-01-02 10:00:00", administrator: "admin", action: "POST /system", action_detail: "set" },
      { number: 2, date: "2026-01-01 09:00:00", administrator: "alice", action: "POST /realm", action_detail: "create" }
    ];
    stubAreas([entries, [], [], [], []]);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain("admin");
    expect(rows[1].textContent).toContain("alice");
  });

  it("should keep at most 5 rows after merging all areas", () => {
    const makeEntries = (area: string, count: number, baseDate: number): AuditData[] =>
      Array.from({ length: count }, (_, i) => ({
        number: baseDate + i,
        date: `2026-01-${String(baseDate + i).padStart(2, "0")} 00:00:00`,
        administrator: "admin",
        action: `POST /${area}`,
        action_detail: ""
      }));

    stubAreas([
      makeEntries("system", 3, 10),
      makeEntries("resolver", 3, 7),
      makeEntries("realm", 3, 4),
      [],
      []
    ]);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll("tbody tr");
    expect(rows.length).toBe(5);
  });

  it("should sort rows by date descending", () => {
    const entries: AuditData[] = [
      { number: 1, date: "2026-01-01 08:00:00", administrator: "a", action: "POST /system", action_detail: "" },
      { number: 2, date: "2026-01-03 12:00:00", administrator: "b", action: "POST /system", action_detail: "" },
      { number: 3, date: "2026-01-02 06:00:00", administrator: "c", action: "POST /system", action_detail: "" }
    ];

    stubAreas([entries, [], [], [], []]);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll("tbody tr");
    expect(rows[0].textContent).toContain("b");
    expect(rows[1].textContent).toContain("c");
    expect(rows[2].textContent).toContain("a");
  });

  it("should render nothing when auditlog right is absent", () => {
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
    fixture.detectChanges();

    expect(auditMock.fetchAuditPage).not.toHaveBeenCalled();
    const table = fixture.nativeElement.querySelector("table");
    expect(table).toBeNull();
  });
});
