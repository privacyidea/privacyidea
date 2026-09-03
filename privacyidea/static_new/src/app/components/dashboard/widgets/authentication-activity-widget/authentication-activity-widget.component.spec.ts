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
import { WidgetInstance } from "@models/dashboard";
import {
  AuthenticationEventSeries,
  AuthenticationLogService,
  AuthenticationLogStatistics
} from "@services/authentication-log/authentication-log.service";
import { AuthService } from "@services/auth/auth.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockAuthenticationLogService } from "@testing/mock-services/mock-authentication-log-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { toFilterDisplay } from "@utils/date-format.utils";
import { of, throwError } from "rxjs";
import { ACTIVITY_RANGES, AuthenticationActivityWidgetComponent } from "./authentication-activity-widget.component";

const instance: WidgetInstance = { id: "activity-1", type: "authentication-activity", x: 0, y: 0, cols: 8, rows: 9 };

const BINS = 4;

function series(event_type: string, outcome: string | null, counts: number[]): AuthenticationEventSeries {
  return { event_type, outcome, counts, total: counts.reduce((a, b) => a + b, 0) };
}

function statistics(events: AuthenticationEventSeries[]): AuthenticationLogStatistics {
  return {
    window: {
      start_time: "2026-03-01T00:00:00+00:00",
      end_time: "2026-03-02T00:00:00+00:00",
      total: events.reduce((sum, entry) => sum + entry.total, 0)
    },
    bins: {
      count: BINS,
      starts: Array.from({ length: BINS }, (_, i) => `2026-03-01T${String(i * 6).padStart(2, "0")}:00:00+00:00`)
    },
    events
  };
}

describe("AuthenticationActivityWidgetComponent", () => {
  let fixture: ComponentFixture<AuthenticationActivityWidgetComponent>;
  let component: AuthenticationActivityWidgetComponent;
  let authMock: MockAuthService;
  let logMock: MockAuthenticationLogService;
  let store: DashboardDataStore;

  function seed(events: AuthenticationEventSeries[]): void {
    logMock.fetchStatistics.mockReturnValue(of(MockPiResponse.fromValue(statistics(events))));
  }

  function create(): void {
    fixture = TestBed.createComponent(AuthenticationActivityWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  }

  function text(selector: string): string {
    return (fixture.nativeElement.querySelector(selector)?.textContent ?? "").trim();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuthenticationActivityWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([{ path: "**", children: [] }]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: AuthenticationLogService, useClass: MockAuthenticationLogService }
      ]
    }).compileComponents();
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    logMock = TestBed.inject(AuthenticationLogService) as unknown as MockAuthenticationLogService;
    store = TestBed.inject(DashboardDataStore);
    store.invalidate();
    jest.spyOn(authMock, "actionAllowed").mockReturnValue(true);
    jest.useFakeTimers({ doNotFake: ["nextTick", "queueMicrotask"] });
    jest.setSystemTime(new Date("2026-03-02T00:00:00Z"));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("sums every series of an outcome into that outcome's headline count", () => {
    seed([
      series("LOGIN_SUCCESS", "success", [1, 2, 0, 0]),
      series("PIN_FAIL", "failure", [0, 1, 0, 0]),
      series("MFA_FAIL", "failure", [0, 0, 2, 0]),
      series("CHALLENGE_TRIGGERED", "pending", [0, 0, 0, 4])
    ]);
    create();

    const summary = component.summary();
    expect(summary.success).toBe(3);
    expect(summary.failure).toBe(3);
    expect(summary.pending).toBe(4);
  });

  it("counts conditional-access rejections as the failures they are", () => {
    // Seeded descending, as the endpoint orders its series; the widget keeps that order rather than re-sorting.
    seed([
      series("USER_LOCKED", "failure", [9, 0, 0, 0]),
      series("IP_BLOCKED", "failure", [7, 0, 0, 0]),
      series("ACCESS_DENIED", "failure", [5, 0, 0, 0]),
      series("PIN_FAIL", "failure", [1, 0, 0, 0])
    ]);
    create();

    // An attempt conditional access turned away did fail, and the table is where the reason gets named.
    expect(component.summary().failure).toBe(22);
    expect(component.summary().reasons.map((reason) => reason.eventType)).toEqual([
      "USER_LOCKED",
      "IP_BLOCKED",
      "ACCESS_DENIED",
      "PIN_FAIL"
    ]);
  });

  it("shares are of every attempt in the window, pending included", () => {
    seed([
      series("LOGIN_SUCCESS", "success", [3, 0, 0, 0]),
      series("PIN_FAIL", "failure", [1, 0, 0, 0]),
      // Counting only resolved attempts would call this 25% failed and hide that most of the window is unanswered.
      series("CHALLENGE_TRIGGERED", "pending", [16, 0, 0, 0])
    ]);
    create();

    const shares = Object.fromEntries(component.summary().rows.map((row) => [row.outcome, component.shareLabel(row)]));
    expect(shares).toEqual({ success: "(15%)", failure: "(5%)", pending: "(80%)" });
  });

  it("shows no share when the window holds no attempt", () => {
    seed([]);
    create();

    for (const row of component.summary().rows) {
      expect(row.share).toBeNull();
      expect(component.shareLabel(row)).toBe("");
    }
  });

  it("prints each row's count next to its bars", () => {
    seed([series("LOGIN_SUCCESS", "success", [2, 1, 0, 0]), series("PIN_FAIL", "failure", [1, 0, 0, 0])]);
    create();

    // The count and the share are separate spans set apart by a gap, so each is asserted on its own rather than
    // through whitespace that only exists visually.
    const cells = Array.from<Element>(fixture.nativeElement.querySelectorAll(".chart-row .chart-value"));
    expect(cells.map((cell) => cell.querySelector(".total")?.textContent?.trim())).toEqual(["3", "1", "0"]);
    expect(cells.map((cell) => cell.querySelector(".share")?.textContent?.trim())).toEqual(["(75%)", "(25%)", "(0%)"]);
  });

  it("renders one bar row per outcome, each with a bar per bin", () => {
    seed([series("LOGIN_SUCCESS", "success", [1, 0, 0, 0]), series("PIN_FAIL", "failure", [0, 2, 0, 0])]);
    create();

    const rows = Array.from<Element>(fixture.nativeElement.querySelectorAll(".chart-row"));
    expect(rows).toHaveLength(3);
    expect(rows[0].querySelectorAll(".bar")).toHaveLength(BINS);
    // The row label is what identifies the series, so the chart never relies on telling the colours apart.
    expect(rows.map((row) => row.querySelector(".chart-label")?.textContent?.trim())).toEqual([
      "Successful",
      "Failed",
      "Pending"
    ]);
  });

  it("charts unanswered attempts at the time they were started", () => {
    // An attempt is unanswered when its latest event is a challenge it never answered, so the bucket dates the
    // attempt rather than the moment it expired: mass in an old bucket means nobody ever answered.
    seed([
      series("CHALLENGE_TRIGGERED", "pending", [3, 0, 0, 0]),
      series("ENROLLMENT_TRIGGERED", "pending", [0, 0, 0, 1])
    ]);
    create();

    const pending = component.summary().rows.find((row) => row.outcome === "pending")!;
    // Every pending series folds into the one row, so it is the outcome's whole volume.
    expect(pending.counts).toEqual([3, 0, 0, 1]);
    expect(pending.total).toBe(4);
  });

  it("keeps the unanswered row on the shared scale so it cannot overstate itself", () => {
    seed([series("LOGIN_SUCCESS", "success", [50, 0, 0, 0]), series("CHALLENGE_TRIGGERED", "pending", [0, 2, 0, 0])]);
    create();

    expect(component.peak()).toBe(50);
    // Still visible despite being 4% of the peak, so a quiet bucket and an empty one never look the same.
    expect(component.barHeight(2)).toBe(4);
  });

  it("scales both rows against one shared peak", () => {
    seed([series("LOGIN_SUCCESS", "success", [10, 0, 0, 0]), series("PIN_FAIL", "failure", [5, 0, 0, 0])]);
    create();

    // A failure row scaled to its own peak would draw 5 failures as tall as 10 successes.
    expect(component.peak()).toBe(10);
    expect(component.barHeight(10)).toBe(100);
    expect(component.barHeight(5)).toBe(50);
  });

  it("keeps a visible sliver for a non-empty bin and nothing for an empty one", () => {
    seed([series("LOGIN_SUCCESS", "success", [1000, 1, 0, 0])]);
    create();

    expect(component.barHeight(0)).toBe(0);
    expect(component.barHeight(1)).toBe(4);
  });

  it("lists every failure reason, leaving the widget body to scroll", () => {
    const reasons = ["A_FAIL", "B_FAIL", "C_FAIL", "D_FAIL", "E_FAIL", "F_FAIL"];
    seed(reasons.map((name, index) => series(name, "failure", [reasons.length - index, 0, 0, 0])));
    create();

    // No cap and so no control to lift one: the frame already scrolls, and the control cost more room than the rows
    // it saved.
    expect(component.summary().reasons.map((reason) => reason.eventType)).toEqual(reasons);
    expect(fixture.nativeElement.querySelectorAll(".reasons-table tbody tr")).toHaveLength(reasons.length);
  });

  it("draws a tick per bin under every row, and the time scale only once", () => {
    seed([series("LOGIN_SUCCESS", "success", [1, 0, 0, 0])]);
    create();

    const axes = fixture.nativeElement.querySelectorAll(".axis-line");
    expect(axes).toHaveLength(3);
    // A tick per bin, laid out like the bars above it, so the two stay aligned however wide the widget is.
    axes.forEach((axis: Element) => expect(axis.querySelectorAll(".axis-tick")).toHaveLength(BINS));
    for (const row of fixture.nativeElement.querySelectorAll(".chart-row")) {
      expect(row.querySelectorAll(".bar")).toHaveLength(row.querySelectorAll(".axis-tick").length);
    }

    // The time scale belongs to the chart as a whole, so it appears once at the bottom.
    expect(fixture.nativeElement.querySelectorAll(".axis-labels")).toHaveLength(1);
    expect(text(".axis-labels")).toContain("now");
  });

  it("shows an empty state when nothing failed", () => {
    seed([series("LOGIN_SUCCESS", "success", [1, 0, 0, 0])]);
    create();

    expect(text(".empty")).toContain("No attempt failed in this range.");
  });

  it("refetches with the selected range and keeps only that range in the store", () => {
    seed([]);
    create();
    expect(logMock.fetchStatistics).toHaveBeenLastCalledWith(expect.any(String), expect.any(String), 24);

    component.selectRange(ACTIVITY_RANGES[3].hours);
    fixture.detectChanges();

    expect(logMock.fetchStatistics).toHaveBeenLastCalledWith(expect.any(String), expect.any(String), 30);
    // The range being shown is cached under its own key; the one left behind is dropped, because refreshAll()
    // refetches every entry the store holds and would otherwise keep re-querying an unseen window.
    expect(store.peek("dashboard:auth-activity:720")).not.toBeNull();
    expect(store.peek("dashboard:auth-activity:24")).toBeNull();
  });

  it("issues one request per dashboard refresh, not one per range ever selected", () => {
    seed([]);
    create();
    component.selectRange(ACTIVITY_RANGES[3].hours);
    fixture.detectChanges();
    logMock.fetchStatistics.mockClear();

    store.refreshAll();

    expect(logMock.fetchStatistics).toHaveBeenCalledTimes(1);
    expect(logMock.fetchStatistics).toHaveBeenCalledWith(expect.any(String), expect.any(String), 30);
  });

  it("changes the range from the button toggle group", () => {
    seed([]);
    create();

    const toggles = fixture.nativeElement.querySelectorAll("mat-button-toggle button");
    expect(toggles).toHaveLength(ACTIVITY_RANGES.length);
    toggles[2].click();
    fixture.detectChanges();

    expect(component.selectedRange().hours).toBe(ACTIVITY_RANGES[2].hours);
    expect(logMock.fetchStatistics).toHaveBeenLastCalledWith(
      expect.any(String),
      expect.any(String),
      ACTIVITY_RANGES[2].bins
    );
  });

  it("requests a window that ends now and spans the selected range", () => {
    seed([]);
    create();

    const [start, end] = logMock.fetchStatistics.mock.calls.at(-1)!;
    const spanHours = (Date.parse(end as string) - Date.parse(start as string)) / 3_600_000;
    expect(spanHours).toBeCloseTo(24, 3);
    expect(Date.parse(end as string)).toBeLessThanOrEqual(Date.now());
  });

  it("advances the window on every refresh instead of replaying the first one", () => {
    seed([]);
    create();
    const first = logMock.fetchStatistics.mock.calls.at(-1) as string[];

    // refreshAll replays the stored factory; a window captured at registration time would repeat these timestamps.
    jest.advanceTimersByTime(60_000);
    store.refreshAll();

    const second = logMock.fetchStatistics.mock.calls.at(-1) as string[];
    expect(Date.parse(second[1])).toBeGreaterThan(Date.parse(first[1]));
    expect(Date.parse(second[0])).toBeGreaterThan(Date.parse(first[0]));
  });

  // Bin starts come from the response, not from the selected range, so these seed the buckets directly. The
  // assertions are patterns and counts rather than fixed strings: formatDate renders in the runner's local zone.
  function seedBuckets(starts: string[], endTime: string): void {
    logMock.fetchStatistics.mockReturnValue(
      of(
        MockPiResponse.fromValue<AuthenticationLogStatistics>({
          window: { start_time: starts[0], end_time: endTime, total: 0 },
          bins: { count: starts.length, starts },
          events: []
        })
      )
    );
  }

  it("always names a time in a bucket label", () => {
    // A bucket runs back from now rather than snapping to midnight, so even a day-wide one spans two clock times and
    // a date alone would misname it.
    const starts = Array.from({ length: 4 }, (_, index) => new Date(Date.UTC(2026, 2, 1 + index)).toISOString());
    seedBuckets(starts, new Date(Date.UTC(2026, 2, 5)).toISOString());
    create();

    for (let index = 0; index < starts.length; index++) {
      expect(component.binTooltip(index)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2} – (\d{4}-\d{2}-\d{2} )?\d{2}:\d{2}$/);
    }
  });

  it("names a time on the axis label, whatever the range", () => {
    // Same reason as a bucket label: the window is measured back from now rather than snapped to midnight, so a bare
    // date would claim a calendar day the chart only partly covers.
    const starts = Array.from({ length: 4 }, (_, index) => new Date(Date.UTC(2026, 2, 1, 8 + index, 37)).toISOString());
    seedBuckets(starts, new Date(Date.UTC(2026, 2, 1, 12, 37)).toISOString());
    create();

    for (const range of ACTIVITY_RANGES) {
      component.selectRange(range.hours);
      fixture.detectChanges();
      expect(component.windowStart()).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
      // Every zone offset is a whole quarter hour, so a label reading midnight would mean the time was dropped.
      expect(component.windowStart()).not.toMatch(/00:00$/);
      expect(text(".axis-labels")).toContain(component.windowStart());
    }
  });

  it("names the second date only for the bucket that crosses midnight", () => {
    // Twenty-four hourly buckets over one day: whatever the zone, exactly one of them straddles midnight, and only
    // that one has to name a second date.
    const starts = Array.from({ length: 24 }, (_, hour) => new Date(Date.UTC(2026, 2, 1, hour)).toISOString());
    seedBuckets(starts, new Date(Date.UTC(2026, 2, 2)).toISOString());
    create();

    const labels = starts.map((_, index) => component.binTooltip(index));
    expect(labels.filter((label) => /\d{4}-\d{2}-\d{2}.*\d{4}-\d{2}-\d{2}/.test(label))).toHaveLength(1);
    expect(labels.every((label) => /^\d{4}-\d{2}-\d{2} \d{2}:\d{2} – /.test(label))).toBe(true);
  });

  it("names both dates for every day-wide bucket", () => {
    const starts = Array.from({ length: 4 }, (_, index) => new Date(Date.UTC(2026, 2, 1 + index)).toISOString());
    seedBuckets(starts, new Date(Date.UTC(2026, 2, 5)).toISOString());
    create();

    for (let index = 0; index < starts.length; index++) {
      expect(component.binTooltip(index)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2} – \d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
    }
  });

  it("exposes every bucket as a table rather than a one-number image label", () => {
    seed([series("LOGIN_SUCCESS", "success", [2, 0, 1, 0]), series("PIN_FAIL", "failure", [0, 3, 0, 0])]);
    create();

    // The bars carry no text, so they are hidden and the table is the text alternative.
    for (const bars of fixture.nativeElement.querySelectorAll(".bars")) {
      expect(bars.getAttribute("aria-hidden")).toBe("true");
    }
    const rows = Array.from<Element>(fixture.nativeElement.querySelectorAll(".visually-hidden tbody tr"));
    expect(rows).toHaveLength(BINS);
    expect(rows.map((row) => Array.from(row.querySelectorAll("td")).map((cell) => cell.textContent?.trim()))).toEqual([
      ["2", "0", "0"],
      ["0", "3", "0"],
      ["1", "0", "0"],
      ["0", "0", "0"]
    ]);
  });

  it("carries the shown window into the log as filter chips, not only as signals", () => {
    seed([series("PIN_FAIL", "failure", [1, 0, 0, 0])]);
    create();
    // A range left over on the log service would otherwise decide what the drill-down shows.
    logMock.timestampFrom.set("2000-01-01T00:00:00Z");
    logMock.timestampTo.set("2000-01-02T00:00:00Z");

    fixture.nativeElement.querySelector(".reasons-table a").click();

    expect(logMock.timestampFrom()).toBe("2026-03-01T00:00:00+00:00");
    expect(logMock.timestampTo()).toBe("2026-03-02T00:00:00+00:00");
    // The chips matter more than the signals: the log derives its time filter from the chip text and clears a bound
    // whose chip is missing, so signals alone are wiped when the page loads.
    const chips = logMock.authenticationLogFilter().filterMap;
    expect(chips.get("start_time")).toBe(toFilterDisplay("2026-03-01T00:00:00+00:00"));
    expect(chips.get("end_time")).toBe(toFilterDisplay("2026-03-02T00:00:00+00:00"));
  });

  it("pre-seeds the log filter when a failure reason is clicked", () => {
    seed([series("PIN_FAIL", "failure", [1, 0, 0, 0])]);
    create();

    fixture.nativeElement.querySelector(".reasons-table a").click();

    expect(logMock.authenticationLogFilter().filterMap.get("event_type")).toBe("PIN_FAIL");
  });

  it("denies without the read right and never fetches", () => {
    jest.spyOn(authMock, "actionAllowed").mockReturnValue(false);
    seed([]);
    create();

    expect(component.state()).toBe("denied");
    expect(logMock.fetchStatistics).not.toHaveBeenCalled();
  });

  it("reports an error when the request fails", () => {
    logMock.fetchStatistics.mockReturnValue(throwError(() => new Error("boom")));
    create();

    expect(component.state()).toBe("error");
  });

  it("reports an error when the response carries a failed result", () => {
    logMock.fetchStatistics.mockReturnValue(of(MockPiResponse.fromError({ code: 400, message: "nope" })));
    create();

    expect(component.state()).toBe("error");
  });
});
