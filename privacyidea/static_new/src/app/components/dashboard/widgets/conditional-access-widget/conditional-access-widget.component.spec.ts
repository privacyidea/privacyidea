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
import { AuthenticationLogService } from "@services/authentication-log/authentication-log.service";
import {
  BlocklistEntry,
  ConditionalAccessOutcomeStatistics,
  ConditionalAccessStateService
} from "@services/conditional-access-state/conditional-access-state.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicy
} from "@services/conditional-access/conditional-access-policy.service";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockAuthenticationLogService } from "@testing/mock-services/mock-authentication-log-service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { MockConditionalAccessStateService } from "@testing/mock-services/mock-conditional-access-state-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { of, Subject, throwError } from "rxjs";
import { ACTIVITY_RANGES } from "@components/dashboard/widgets/activity-range";
import { ConditionalAccessWidgetComponent, RESTRICTION_KINDS } from "./conditional-access-widget.component";

const instance: WidgetInstance = {
  id: "conditional-access-1",
  type: "conditional-access",
  x: 0,
  y: 0,
  cols: 8,
  rows: 6
};

function makePolicy(overrides: Partial<ConditionalAccessPolicy>): ConditionalAccessPolicy {
  return {
    id: 1,
    name: "policy",
    time_window_seconds: 600,
    enabled: true,
    dry_run: false,
    priority: 1,
    target: "user",
    count_mode: "PER_REQUEST",
    reset_on_success: true,
    counter_types_to_track: ["PASSWORD_FAIL"],
    stages: [],
    ...overrides
  };
}

const MS_PER_HOUR = 3_600_000;

// Timestamps are relative to the moment the test runs, since the widget's window ends at "now" and a future-dated
// fixture would fall outside it.
function hoursAgo(hours: number): string {
  return new Date(Date.now() - hours * MS_PER_HOUR).toISOString();
}

function makeBlock(overrides: Partial<BlocklistEntry>): BlocklistEntry {
  return {
    identifier: "10.0.0.1",
    permanent: false,
    block_expires_at: new Date(Date.now() + MS_PER_HOUR).toISOString(),
    seconds_remaining: 600,
    block_cause: "POLICY",
    blocked_at: hoursAgo(2),
    error_message: null,
    ...overrides
  };
}

// The outcome history as the endpoint hands it back: already bucketed, one series per action type. The buckets are a
// day apart with the newest one today, so the window overlaps the lock and block fixtures above.
function history(...series: { action_type: string; counts: number[] }[]): ConditionalAccessOutcomeStatistics {
  const bucketCount = series[0].counts.length;
  const starts = Array.from({ length: bucketCount }, (_, index) => hoursAgo((bucketCount - index) * 24));
  return {
    window: { start_time: starts[0], end_time: hoursAgo(0), total: 0 },
    bins: { count: bucketCount, starts },
    outcomes: series.map((entry) => ({ ...entry, total: entry.counts.reduce((a, b) => a + b, 0) }))
  };
}

describe("ConditionalAccessWidgetComponent", () => {
  let fixture: ComponentFixture<ConditionalAccessWidgetComponent>;
  let component: ConditionalAccessWidgetComponent;
  let authMock: MockAuthService;
  let policyMock: MockConditionalAccessPolicyService;
  let stateMock: MockConditionalAccessStateService;
  let store: DashboardDataStore;

  // Finds the badge in the value cell of the row labeled *label*, so an assertion can name which row it checks.
  function rowBadge(label: string): HTMLElement | null {
    const rows: HTMLTableRowElement[] = Array.from(fixture.nativeElement.querySelectorAll(".ca-table tr"));
    const row = rows.find((candidate) => candidate.cells[0]?.textContent?.trim() === label);
    return row?.cells[1]?.querySelector("span") ?? null;
  }

  // Create the widget after the mocks have been seeded: the data is fetched in ngOnInit.
  function create(): void {
    fixture = TestBed.createComponent(ConditionalAccessWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        // A catch-all route so the test router always finds a match when a widget link is clicked.
        provideRouter([{ path: "**", children: [] }]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: AuthenticationLogService, useClass: MockAuthenticationLogService },
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: ConditionalAccessStateService, useClass: MockConditionalAccessStateService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.actionAllowed.mockReturnValue(true);
    policyMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    stateMock = TestBed.inject(ConditionalAccessStateService) as unknown as MockConditionalAccessStateService;
    store = TestBed.inject(DashboardDataStore);

    policyMock.policies.set([
      makePolicy({ id: 1, name: "Brute force" }),
      makePolicy({ id: 2, name: "Spraying", enabled: true, dry_run: true }),
      makePolicy({ id: 3, name: "Old policy", enabled: false })
    ]);
    stateMock.setLockedUsersCount(["permanent"], 2);
    stateMock.setLockedUsersCount(["temporary"], 3);
    stateMock.setLockedUsersCount(["expired"], 4);
    stateMock.setBlocklistEntries([
      makeBlock({ identifier: "10.0.0.1", blocked_at: hoursAgo(2) }),
      // An explicit time rather than makeBlock's default: two separate hoursAgo(2) calls tie only while they land in
      // the same millisecond, and the order of these two is asserted below.
      makeBlock({
        identifier: "10.0.0.2",
        permanent: true,
        block_expires_at: null,
        seconds_remaining: null,
        blocked_at: hoursAgo(3)
      }),
      makeBlock({ identifier: "10.0.0.3", seconds_remaining: 0, blocked_at: hoursAgo(5) })
    ]);
  });

  afterEach(() => fixture?.destroy());

  it("should create and extend the DashboardWidget base", () => {
    create();
    expect(component).toBeTruthy();
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata and size constraints", () => {
    expect(ConditionalAccessWidgetComponent.type).toBe("conditional-access");
    expect(ConditionalAccessWidgetComponent.title).toBeTruthy();
    expect(ConditionalAccessWidgetComponent.icon).toBe("security");
    expect(ConditionalAccessWidgetComponent.defaultSize).toEqual({ cols: 6, rows: 11 });
    expect(ConditionalAccessWidgetComponent.minSize).toEqual({ cols: 6, rows: 5 });
    expect(ConditionalAccessWidgetComponent.maxSize).toEqual({ cols: 16, rows: 12 });
  });

  it("should require any one of the three conditional-access read rights", () => {
    expect(ConditionalAccessWidgetComponent.requiredAction).toEqual([
      "conditional_access_policy_read",
      "user_lock_read",
      "blocklist_read"
    ]);
  });

  it("should count a dry-run policy on its own rather than as enforcing", () => {
    create();
    expect(component.summary().policies).toEqual({ total: 3, enforcing: 1, dryRun: 1, disabled: 1 });
  });

  it("should split the lock counts per state and add up the ones in force", () => {
    create();
    expect(component.summary().lockedUsers).toEqual({ permanent: 2, temporary: 3, expired: 4, inForce: 5 });
    expect(stateMock.countLockedUsers).toHaveBeenCalledWith(["permanent"]);
    expect(stateMock.countLockedUsers).toHaveBeenCalledWith(["temporary"]);
    expect(stateMock.countLockedUsers).toHaveBeenCalledWith(["expired"]);
  });

  it("should split the blocklist by state, counting a run-out entry as expired", () => {
    create();
    expect(component.summary().blockedIps).toEqual({ permanent: 1, temporary: 1, expired: 1, inForce: 2 });
  });

  it("should sum the expired locks and blocks into the stale-record count", () => {
    create();
    expect(component.staleRecords()).toBe(5);
  });

  it("should highlight only the blocks in force, most recently blocked first", () => {
    stateMock.setBlocklistEntries([
      makeBlock({ identifier: "10.0.0.1", blocked_at: hoursAgo(5) }),
      makeBlock({ identifier: "10.0.0.2", blocked_at: hoursAgo(1) }),
      makeBlock({ identifier: "10.0.0.9", seconds_remaining: 0, blocked_at: hoursAgo(3) })
    ]);
    create();

    expect(component.summary().highlights.map((entry) => entry.label)).toEqual(["10.0.0.2", "10.0.0.1"]);
  });

  it("should list every block in force and report the locks it has no records for", () => {
    stateMock.setBlocklistEntries(
      Array.from({ length: 7 }, (_, index) =>
        makeBlock({ identifier: `10.0.0.${index}`, blocked_at: hoursAgo(index + 1) })
      )
    );
    create();

    // All seven blocks are listed; the five locks in force have no records in this mock, so they are the remainder.
    expect(component.summary().highlights).toHaveLength(7);
    expect(fixture.nativeElement.querySelectorAll(".ca-highlight-cell")).toHaveLength(7);
    expect(component.hiddenHighlightCount()).toBe(5);
    expect(fixture.nativeElement.textContent).toContain("5 more in force");
  });

  it("should not report hidden restrictions when the highlights show them all", () => {
    stateMock.setLockedUsersCount(["permanent"], 0);
    stateMock.setLockedUsersCount(["temporary"], 0);
    create();
    expect(component.hiddenHighlightCount()).toBe(0);
    expect(fixture.nativeElement.textContent).not.toContain("more in force");
  });

  it("should list the locked users alongside the blocked IPs, most recent first", () => {
    stateMock.setLockedUsers([
      {
        resolver: "resolver1",
        uid: "1000",
        realm: "defrealm",
        username: "cornelius",
        permanent: false,
        lock_expires_at: new Date(Date.now() + MS_PER_HOUR).toISOString(),
        seconds_remaining: 600,
        lock_cause: "POLICY",
        locked_at: hoursAgo(1),
        error_message: null
      }
    ]);
    create();

    const highlights = component.summary().highlights;
    expect(highlights.map((entry) => entry.label)).toEqual(["cornelius@defrealm", "10.0.0.1", "10.0.0.2"]);
    expect(highlights[0].kind).toBe("user");
    expect(component.highlightLink(highlights[0])).toBe(ROUTE_PATHS.LOCKED_USERS);
    expect(component.highlightLink(highlights[1])).toBe(ROUTE_PATHS.AUTHENTICATION_LOG);
    expect(fixture.nativeElement.textContent).toContain("cornelius@defrealm");
    // A blocked IP shows an "IP" label over the block icon; a locked user shows only the lock icon.
    expect(fixture.nativeElement.querySelectorAll(".icon-block-ip-text")).toHaveLength(2);
    expect(fixture.nativeElement.querySelector(".icon-block-ip-text").textContent).toBe("IP");
  });

  it("should leave a locked user outside the selected range out of the list once the range is narrowed", () => {
    stateMock.setLockedUsers([
      {
        resolver: "resolver1",
        uid: "1000",
        realm: "defrealm",
        username: "ancient",
        permanent: true,
        lock_expires_at: null,
        seconds_remaining: null,
        lock_cause: "POLICY",
        locked_at: hoursAgo(400),
        error_message: null
      }
    ]);
    create();
    // The window is the fetched one, so a lock from within it is in range until the brush is narrowed.
    expect(component.summary().highlights.map((entry) => entry.label)).toContain("ancient@defrealm");

    // Almost the whole window brushed away, leaving only its last hundredth - which the 400-hour-old lock is not in.
    component.onRangeStartInput(99);
    fixture.detectChanges();

    expect(component.summary().highlights.map((entry) => entry.label)).not.toContain("ancient@defrealm");
  });

  it("should render the counts, the highlighted IPs and their state", () => {
    create();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("Enforcing policies");
    expect(text).toContain("Users locked");
    expect(text).toContain("IPs blocked");
    expect(text).toContain("10.0.0.1");
    expect(text).toContain("10.0.0.2");
    // The expired entry belongs on the blocklist page, not in the highlights.
    expect(text).not.toContain("10.0.0.3");
    expect(text).toContain("permanent");
    expect(text).toContain("temporary");
  });

  it("should flag a restriction in force and leave a zero count unflagged", () => {
    create();
    expect(rowBadge("Users locked")?.className).toBe("highlight-false");
    expect(rowBadge("Users locked")?.textContent).toBe("5");

    stateMock.setLockedUsersCount(["permanent"], 0);
    stateMock.setLockedUsersCount(["temporary"], 0);
    component.reload();
    fixture.detectChanges();

    expect(component.summary().lockedUsers?.inForce).toBe(0);
    expect(rowBadge("Users locked")?.className).toBe("highlight-true");
  });

  it("should tell the admin when nothing is blocked", () => {
    stateMock.setBlocklistEntries([]);
    create();
    expect(fixture.nativeElement.textContent).toContain(
      "No IP is blocked and no user locked in the selected time range."
    );
  });

  it("should name the expiry of a temporary block in its tooltip", () => {
    create();
    const expiry = new Date(Date.now() + MS_PER_HOUR).toISOString();
    const tooltip = component.expiresTooltip({
      label: "10.0.0.1",
      permanent: false,
      at: hoursAgo(1),
      expiresAt: expiry,
      kind: "ip"
    });
    expect(tooltip).toContain("In force until");
    expect(tooltip).not.toContain(expiry);
  });

  it("should pre-seed the authentication-log filter with a highlighted IP", () => {
    create();
    const logService = TestBed.inject(AuthenticationLogService) as unknown as MockAuthenticationLogService;

    const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll("a[href]"));
    const link = links.find((candidate) => candidate.textContent?.trim() === "10.0.0.1");
    link?.click();
    fixture.detectChanges();

    expect(logService.authenticationLogFilter().filterMap.get("source_ip")).toBe("10.0.0.1");
  });

  describe("activity histogram and range slider", () => {
    it("should normalize the server's buckets to the busiest one", () => {
      // The bucketing is the endpoint's; the widget only scales the bars against the busiest bucket.
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [0, 1, 4, 0] }));
      create();

      const bars = component.activityHistogram();
      expect(bars).toEqual([0, 0.25, 1, 0]);
      expect(component.restrictionsInRange()).toBe(5);
    });

    it("should chart every action that creates a restriction in one row of bars", () => {
      // Locks and IP blocks are separate series in the response; the histogram is their sum, as its title says.
      stateMock.setOutcomeStatistics(
        history(
          { action_type: "LOCK_USER", counts: [1, 0, 0, 0] },
          { action_type: "PERMANENT_BLOCK_IP", counts: [1, 0, 2, 0] }
        )
      );
      create();

      expect(component.activityHistogram()).toEqual([1, 0, 1, 0]);
      expect(component.restrictionsInRange()).toBe(4);
    });

    it("should chart only the kinds of restriction selected, and count what it charts", () => {
      stateMock.setOutcomeStatistics(
        history(
          { action_type: "LOCK_USER", counts: [2, 0, 0, 0] },
          { action_type: "PERMANENT_BLOCK_IP", counts: [0, 0, 6, 0] }
        )
      );
      create();
      // Both to begin with, so the chart opens on every restriction the window holds.
      expect(component.shownKinds()).toEqual(["users", "ips"]);
      expect(component.restrictionsInRange()).toBe(8);

      component.selectKinds(["users"]);
      fixture.detectChanges();

      // The number beside the title counts what the bars show, or it would contradict them.
      expect(component.restrictionsInRange()).toBe(2);
      expect(fixture.nativeElement.textContent).toContain("2 in range");
      // And the bars rescale to what is left, the way taking a row off the activity chart does: two locks are the
      // busiest bucket now that the six blocks are off.
      expect(component.activityHistogram()).toEqual([1, 0, 0, 0]);
    });

    it("should keep asking for every kind, whichever are charted", () => {
      create();
      const actions = stateMock.fetchOutcomeStatistics.mock.calls.at(-1)![3];
      stateMock.fetchOutcomeStatistics.mockClear();

      component.selectKinds(["ips"]);
      fixture.detectChanges();

      // Hiding a kind leaves its series out of the sum; the response already carries both, so switching costs no
      // request and switching back costs nothing either.
      expect(stateMock.fetchOutcomeStatistics).not.toHaveBeenCalled();
      expect(actions).toEqual(["LOCK_USER", "PERMANENT_LOCK_USER", "BLOCK_IP", "PERMANENT_BLOCK_IP"]);
    });

    it("should keep the last kind on the chart", () => {
      create();

      // An empty plot with a live brush under it is not a view of anything, and Material's multi-select group will
      // happily deselect everything.
      component.selectKinds([]);
      fixture.detectChanges();

      expect(component.shownKinds()).toEqual(["users", "ips"]);
    });

    it("should show both toggle groups above the histogram rather than in the widget header", () => {
      create();

      // The header governs the whole widget; these govern one of its sections, and both are readable without being
      // opened.
      const groups = fixture.nativeElement.querySelectorAll(".ca-range-controls mat-button-toggle-group");
      expect(groups).toHaveLength(2);
      expect(groups[1].getAttribute("aria-label")).toBe("Restrictions to chart");
      expect(fixture.nativeElement.querySelectorAll(".ca-range-controls mat-button-toggle")).toHaveLength(
        ACTIVITY_RANGES.length + RESTRICTION_KINDS.length
      );
    });

    it("should count a lock that the live state has long forgotten", () => {
      // The point of reading the outcome history: a lock that expired and was purged is gone from user_lock_state
      // and block_list, and still belongs in a chart of when restrictions were imposed.
      stateMock.setBlocklistEntries([]);
      stateMock.setLockedUsers([]);
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [3, 0, 0, 0] }));
      create();

      expect(component.restrictionsInRange()).toBe(3);
      expect(component.summary().highlights).toEqual([]);
    });

    it("should ask for the actions that create a restriction over the selected preset's window", () => {
      create();

      const [start, end, bins, actions] = stateMock.fetchOutcomeStatistics.mock.calls.at(-1)!;
      expect(actions).toEqual(["LOCK_USER", "PERMANENT_LOCK_USER", "BLOCK_IP", "PERMANENT_BLOCK_IP"]);
      // The preset owns the window and how finely it is cut, so the request is what it describes. Compared by span
      // and by ending at about now, not by an exact instant: the default range is measured back from the present, so
      // the assertion cannot name the same millisecond the request was built with.
      const expected = component.selectedRange().window(new Date());
      expect(bins).toBe(expected.bins);
      expect(Date.parse(end as string) - Date.parse(start as string)).toBe(
        expected.end.getTime() - expected.start.getTime()
      );
      expect(Date.now() - Date.parse(end as string)).toBeLessThan(2_000);
    });

    it("should refetch for the window a preset names and drop the one left behind", () => {
      create();
      expect(component.selectedRange().id).toBe("24h");

      // The hour, whose window is a rolling one and so an exact twelve five-minute buckets whenever it is asked for.
      component.selectRange("1h");
      fixture.detectChanges();

      const [start, end, bins] = stateMock.fetchOutcomeStatistics.mock.calls.at(-1)!;
      expect(bins).toBe(12);
      expect(Date.parse(end as string) - Date.parse(start as string)).toBe(MS_PER_HOUR);
      // Each preset caches the history under its own key, and the one no longer shown is dropped: refreshAll()
      // replays every entry the store holds, and a stale key would keep re-querying a window nobody is looking at.
      expect(store.peek("dashboard:conditional-access:history:1h")).not.toBeNull();
      expect(store.peek("dashboard:conditional-access:history:24h")).toBeNull();
      // The rest of the widget does not depend on the window, so it keeps the entry it already had.
      expect(store.peek("dashboard:conditional-access")).not.toBeNull();
    });

    it("should read only the history when a preset changes, not the whole widget", () => {
      create();
      policyMock.getPolicies.mockClear();
      stateMock.countLockedUsers.mockClear();
      stateMock.fetchLockedUsers.mockClear();
      stateMock.fetchBlocklist.mockClear();
      stateMock.fetchOutcomeStatistics.mockClear();

      component.selectRange("7d");
      fixture.detectChanges();

      // The window belongs to the history request alone; the policies, the lock counts and the blocklist do not
      // depend on it, so a preset click costs one request rather than six.
      expect(stateMock.fetchOutcomeStatistics).toHaveBeenCalledTimes(1);
      expect(policyMock.getPolicies).not.toHaveBeenCalled();
      expect(stateMock.countLockedUsers).not.toHaveBeenCalled();
      expect(stateMock.fetchLockedUsers).not.toHaveBeenCalled();
      expect(stateMock.fetchBlocklist).not.toHaveBeenCalled();
    });

    it("should keep the whole section up while a preset's window is being fetched", () => {
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [1, 2, 3, 4] }));
      create();
      expect(component.restrictionsInRange()).toBe(10);

      // The next window's response is held back, which is the moment a store entry for a fresh key has nothing in it.
      const pending = new Subject<PiResponse<ConditionalAccessOutcomeStatistics>>();
      stateMock.fetchOutcomeStatistics.mockReturnValue(pending.asObservable());
      component.selectRange("7d");
      fixture.detectChanges();

      // Title, controls and chart all stay: taking them off the widget and putting them back is a worse answer to a
      // request in flight than the frame's own spinner.
      expect(component.hasHistory()).toBe(true);
      expect(component.state()).toBe("ready");
      expect(fixture.nativeElement.textContent).toContain("Blocks and locks over time");
      expect(fixture.nativeElement.querySelectorAll(".ca-range-controls mat-button-toggle-group")).toHaveLength(2);
      expect(fixture.nativeElement.querySelectorAll(".ca-activity-bar")).toHaveLength(4);

      pending.next(MockPiResponse.fromValue(history({ action_type: "LOCK_USER", counts: [5, 0] })));
      fixture.detectChanges();

      expect(component.restrictionsInRange()).toBe(5);
    });

    it("should open the brush again when a preset changes the window", () => {
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [1, 2, 3, 4] }));
      create();
      component.onRangeEndInput(2);
      expect(component.restrictionsInRange()).toBe(3);

      component.selectRange("7d");
      fixture.detectChanges();

      // The window has moved under the old positions, so keeping them would silently rename the selected span.
      expect(component.rangeStart()).toBe(0);
      expect(component.rangeEnd()).toBe(component.binCount());
    });

    it("should render one element per bucket the response carries", () => {
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [1, 0, 2, 0] }));
      create();

      expect(fixture.nativeElement.querySelectorAll(".ca-activity-bar")).toHaveLength(4);
      expect(fixture.nativeElement.textContent).toContain("3 in range");
    });

    it("should narrow the counted restrictions and the highlights when a thumb moves in", () => {
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [0, 0, 0, 3] }));
      create();
      expect(component.restrictionsInRange()).toBe(3);

      // Everything but the oldest hundredth of the window brushed away: the records are hours old and the counted
      // bucket is the newest one, so neither is left in the selection.
      component.onRangeEndInput(1);
      fixture.detectChanges();

      expect(component.restrictionsInRange()).toBe(0);
      expect(component.summary().highlights).toEqual([]);
      expect(fixture.nativeElement.textContent).toContain(
        "No IP is blocked and no user locked in the selected time range."
      );
    });

    it("should never let the thumbs close the span", () => {
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [1, 2, 3, 4] }));
      create();

      // A closed brush would count nothing, so the chart would read as empty rather than as unselected.
      component.onRangeEndInput(0);
      expect(component.rangeEnd()).toBe(1);

      component.onRangeEndInput(4);
      component.onRangeStartInput(4);
      expect(component.rangeStart()).toBe(3);
    });

    it("should label the end of the fetched window as now", () => {
      stateMock.setOutcomeStatistics(history({ action_type: "LOCK_USER", counts: [1, 2, 3, 4] }));
      create();

      // The window ends at the moment it was fetched, and the brush starts open, so the upper label reads "now"
      // rather than a timestamp a second in the past.
      expect(component.rangeSummaryTo()).toBe("now");

      component.onRangeEndInput(2);
      fixture.detectChanges();
      expect(component.rangeSummaryTo()).not.toBe("now");
    });

    it("should label a thumb with the timestamp it stands for", () => {
      create();
      expect(component.formatSliderThumb(0)).toMatch(/^\d{4}-\d{2}-\d{2}/);
    });
  });

  describe("permissions", () => {
    it("should render nothing but the denial when no conditional-access right is granted", () => {
      authMock.actionAllowed.mockReturnValue(false);
      create();

      expect(component.state()).toBe("denied");
      expect(policyMock.getPolicies).not.toHaveBeenCalled();
      expect(stateMock.countLockedUsers).not.toHaveBeenCalled();
      expect(stateMock.fetchBlocklist).not.toHaveBeenCalled();
    });

    it("should leave out the history when the authentication-log right is missing", () => {
      // The outcomes hang off the log entries that caused them, so they are read under the log's right. An admin with
      // the conditional-access rights alone keeps the numbers and the restrictions list, and gets no history.
      authMock.actionAllowed.mockImplementation((action: string) => action !== "authentication_log_read");
      create();

      expect(component.state()).toBe("ready");
      expect(stateMock.fetchOutcomeStatistics).not.toHaveBeenCalled();
      expect(component.hasHistory()).toBe(false);
      expect(fixture.nativeElement.textContent).not.toContain("Blocks and locks over time");
      // The rest of the widget is untouched.
      expect(component.summary().blockedIps).not.toBeNull();
    });

    it("should leave out the areas whose right is missing and keep the rest", () => {
      authMock.actionAllowed.mockImplementation((action: string) => action === "blocklist_read");
      create();

      expect(component.state()).toBe("ready");
      expect(component.summary().policies).toBeNull();
      expect(component.summary().lockedUsers).toBeNull();
      expect(component.summary().blockedIps).not.toBeNull();
      expect(policyMock.getPolicies).not.toHaveBeenCalled();
      expect(stateMock.countLockedUsers).not.toHaveBeenCalled();

      const text = fixture.nativeElement.textContent;
      expect(text).toContain("IPs blocked");
      expect(text).not.toContain("Enforcing policies");
      expect(text).not.toContain("Users locked");
    });

    it("should not count the skipped areas as failures", () => {
      authMock.actionAllowed.mockImplementation((action: string) => action === "conditional_access_policy_read");
      create();

      expect(component.state()).toBe("ready");
      expect(component.staleRecords()).toBe(0);
    });
  });

  describe("failure handling", () => {
    it("should report an error when the very first load fails", () => {
      policyMock.getPolicies.mockReturnValue(throwError(() => new Error("boom")));
      create();

      expect(component.state()).toBe("error");
      expect(component.refreshFailed()).toBe(false);
      expect(fixture.nativeElement.textContent).toContain("Could not load data.");
    });

    it("should report an error when a response carries a failed status", () => {
      policyMock.getPolicies.mockReturnValue(
        of(MockPiResponse.fromError<ConditionalAccessPolicy[]>({ message: "nope" }))
      );
      create();

      expect(component.state()).toBe("error");
    });

    it("should keep the loaded summary and mark the widget when a later refresh fails", () => {
      create();
      expect(component.summary().blockedIps?.inForce).toBe(2);

      stateMock.fetchBlocklist.mockReturnValue(throwError(() => new Error("boom")));
      store.refreshAll();
      fixture.detectChanges();

      expect(component.state()).toBe("ready");
      expect(component.refreshFailed()).toBe(true);
      expect(component.summary().blockedIps?.inForce).toBe(2);
      expect(fixture.nativeElement.textContent).not.toContain("Could not load data.");
    });

    it("should clear the failure marker once a later refresh succeeds", () => {
      create();
      stateMock.fetchBlocklist.mockReturnValue(throwError(() => new Error("boom")));
      store.refreshAll();
      fixture.detectChanges();
      expect(component.refreshFailed()).toBe(true);

      stateMock.fetchBlocklist.mockReturnValue(
        of(MockPiResponse.fromValue<BlocklistEntry[]>([makeBlock({ identifier: "10.0.0.7" })]))
      );
      component.reload();
      fixture.detectChanges();

      expect(component.refreshFailed()).toBe(false);
      expect(component.summary().highlights.map((entry) => entry.label)).toEqual(["10.0.0.7"]);
    });
  });
});
