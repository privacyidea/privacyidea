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
import { Resolver, Resolvers, ResolverService } from "@services/resolver/resolver.service";
import { ResolverTimingEntry, SystemService } from "@services/system/system.service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of } from "rxjs";
import { ResolverTimingWidgetComponent } from "./resolver-timing-widget.component";

function makeResponse<T>(value: T): PiResponse<T> {
  return {
    id: 1,
    jsonrpc: "2.0",
    signature: "",
    time: 0,
    version: "",
    versionnumber: "",
    detail: {},
    result: { status: true, value }
  };
}

function makeResolver(name: string, type: Resolver["type"]): Resolver {
  return { resolvername: name, type, data: {}, censor_keys: [] };
}

describe("ResolverTimingWidgetComponent", () => {
  let fixture: ComponentFixture<ResolverTimingWidgetComponent>;
  let component: ResolverTimingWidgetComponent;
  let systemMock: MockSystemService;
  let resolverMock: MockResolverService;

  const instance: WidgetInstance = { id: "resolver-timing-1", type: "resolver-timing", x: 0, y: 0, cols: 10, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ResolverTimingWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: SystemService, useClass: MockSystemService },
        { provide: ResolverService, useClass: MockResolverService }
      ]
    }).compileComponents();

    systemMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    systemMock.getResolverTiming.mockReturnValue(
      of(
        makeResponse<ResolverTimingEntry[]>([
          {
            labels: { resolver: "ldapresolver", resolver_type: "ldapresolver", op: "get_user_info" },
            count: 42,
            avg: 0.02,
            p50: 0.015,
            p95: 0.6,
            max: 0.8,
            buckets: [[1, 42]]
          },
          {
            labels: { resolver: "sqlresolver", resolver_type: "sqlresolver", op: "check_pass" },
            count: 10,
            avg: 0.01,
            p50: 0.01,
            p95: 0.02,
            max: 0.03,
            buckets: [[1, 10]]
          }
        ])
      )
    );

    resolverMock = TestBed.inject(ResolverService) as unknown as MockResolverService;
    resolverMock.listResolvers.mockReturnValue(
      of(
        makeResponse<Resolvers>({
          ldapresolver: makeResolver("ldapresolver", "ldapresolver"),
          sqlresolver: makeResolver("sqlresolver", "sqlresolver")
        })
      )
    );

    fixture = TestBed.createComponent(ResolverTimingWidgetComponent);
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
    expect(ResolverTimingWidgetComponent.type).toBe("resolver-timing");
    expect(ResolverTimingWidgetComponent.title).toBeTruthy();
    expect(ResolverTimingWidgetComponent.icon).toBe("speed");
  });

  it("should override the static size constraints", () => {
    expect(ResolverTimingWidgetComponent.defaultSize).toEqual({ cols: 10, rows: 5 });
    expect(ResolverTimingWidgetComponent.minSize).toEqual({ cols: 6, rows: 4 });
    expect(ResolverTimingWidgetComponent.maxSize).toEqual({ cols: 18, rows: 10 });
  });

  it("should render a row per resolver/op entry sorted by p95 descending", () => {
    const rows = fixture.nativeElement.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain("ldapresolver");
    expect(rows[1].textContent).toContain("sqlresolver");
  });

  it("should convert seconds to rounded milliseconds", () => {
    const firstRowCells = fixture.nativeElement.querySelectorAll("tbody tr:first-child td");
    expect(firstRowCells[3].textContent?.trim()).toBe("20");
    expect(firstRowCells[4].textContent?.trim()).toBe("600");
    expect(firstRowCells[5].textContent?.trim()).toBe("800");
  });

  it("should badge the p95 cell using the shared highlight classes", () => {
    const badges: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll(".resolver-timing-table tbody span"));
    expect(badges[0].className).toBe("highlight-false");
    expect(badges[1].className).toBe("highlight-true");
  });

  it("should include a configured resolver with no recorded activity as a zero-count row", () => {
    resolverMock.listResolvers.mockReturnValue(
      of(
        makeResponse<Resolvers>({
          ldapresolver: makeResolver("ldapresolver", "ldapresolver"),
          sqlresolver: makeResolver("sqlresolver", "sqlresolver"),
          idle_resolver: makeResolver("idle_resolver", "httpresolver")
        })
      )
    );

    const idleFixture = TestBed.createComponent(ResolverTimingWidgetComponent);
    idleFixture.componentRef.setInput("instance", instance);
    idleFixture.detectChanges();

    const rows: HTMLElement[] = Array.from(idleFixture.nativeElement.querySelectorAll("tbody tr"));
    expect(rows.length).toBe(3);
    const idleRow = rows.find((row) => row.textContent?.includes("idle_resolver"));
    expect(idleRow).toBeTruthy();
    const cells = idleRow?.querySelectorAll("td");
    expect(cells?.[1].textContent?.trim()).toBe("—");
    expect(cells?.[2].textContent?.trim()).toBe("0");
    expect(cells?.[3].textContent?.trim()).toBe("—");
    expect(idleRow?.querySelector("span")?.className).toBe("highlight-disabled");
    idleFixture.destroy();
  });

  it("should not add a duplicate idle row for a resolver that already has activity across multiple operations", () => {
    systemMock.getResolverTiming.mockReturnValue(
      of(
        makeResponse<ResolverTimingEntry[]>([
          {
            labels: { resolver: "ldapresolver", resolver_type: "ldapresolver", op: "get_user_info" },
            count: 42,
            avg: 0.02,
            p50: 0.015,
            p95: 0.6,
            max: 0.8,
            buckets: [[1, 42]]
          },
          {
            labels: { resolver: "ldapresolver", resolver_type: "ldapresolver", op: "check_pass" },
            count: 5,
            avg: 0.03,
            p50: 0.03,
            p95: 0.04,
            max: 0.05,
            buckets: [[1, 5]]
          },
          {
            labels: { resolver: "sqlresolver", resolver_type: "sqlresolver", op: "check_pass" },
            count: 10,
            avg: 0.01,
            p50: 0.01,
            p95: 0.02,
            max: 0.03,
            buckets: [[1, 10]]
          }
        ])
      )
    );
    resolverMock.listResolvers.mockReturnValue(
      of(
        makeResponse<Resolvers>({
          ldapresolver: makeResolver("ldapresolver", "ldapresolver"),
          sqlresolver: makeResolver("sqlresolver", "sqlresolver"),
          idle_resolver: makeResolver("idle_resolver", "httpresolver")
        })
      )
    );

    const mixedFixture = TestBed.createComponent(ResolverTimingWidgetComponent);
    mixedFixture.componentRef.setInput("instance", instance);
    mixedFixture.detectChanges();

    const rows: HTMLElement[] = Array.from(mixedFixture.nativeElement.querySelectorAll("tbody tr"));
    // 2 ldapresolver ops + 1 sqlresolver op + 1 idle_resolver placeholder = 4, never 6.
    expect(rows.length).toBe(4);

    const ldapRows = rows.filter((row) => row.textContent?.includes("ldapresolver"));
    expect(ldapRows.length).toBe(2);
    expect(ldapRows.some((row) => row.textContent?.includes("get_user_info"))).toBe(true);
    expect(ldapRows.some((row) => row.textContent?.includes("check_pass"))).toBe(true);
    // Neither ldapresolver row is the idle placeholder (count 0, "—" operation).
    ldapRows.forEach((row) => {
      const cells = row.querySelectorAll("td");
      expect(cells[1].textContent?.trim()).not.toBe("—");
      expect(cells[2].textContent?.trim()).not.toBe("0");
    });

    const sqlRows = rows.filter((row) => row.textContent?.includes("sqlresolver"));
    expect(sqlRows.length).toBe(1);

    const idleRows = rows.filter((row) => row.textContent?.includes("idle_resolver"));
    expect(idleRows.length).toBe(1);

    mixedFixture.destroy();
  });
});
