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
import { ResolverTimingEntry, SystemService } from "@services/system/system.service";
import { MockSystemService } from "@testing/mock-services/mock-system-service";
import { of } from "rxjs";
import { ResolverTimingWidgetComponent } from "./resolver-timing-widget.component";

function makeResponse(entries: ResolverTimingEntry[]): PiResponse<ResolverTimingEntry[]> {
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

describe("ResolverTimingWidgetComponent", () => {
  let fixture: ComponentFixture<ResolverTimingWidgetComponent>;
  let component: ResolverTimingWidgetComponent;
  let systemMock: MockSystemService;

  const instance: WidgetInstance = { id: "resolver-timing-1", type: "resolver-timing", x: 0, y: 0, cols: 10, rows: 5 };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ResolverTimingWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    systemMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    systemMock.getResolverTiming.mockReturnValue(
      of(
        makeResponse([
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
});
