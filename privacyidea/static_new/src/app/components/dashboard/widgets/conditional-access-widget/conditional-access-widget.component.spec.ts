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
import { ROUTE_PATHS } from "@app/route_paths";
import { DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { AuthenticationLogService } from "@services/authentication-log/authentication-log.service";
import {
  BlocklistEntry,
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
import { of, throwError } from "rxjs";
import { ConditionalAccessWidgetComponent } from "./conditional-access-widget.component";

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
      makeBlock({ identifier: "10.0.0.2", permanent: true, block_expires_at: null, seconds_remaining: null }),
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
    // The window reaches back to the oldest record, so the lock is in range until the range is narrowed.
    expect(component.summary().highlights.map((entry) => entry.label)).toContain("ancient@defrealm");

    component.applyStartPreset({ label: "Last 24 hours", ageMs: 86_400_000 });
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
    it("should bucket every recorded block, expired ones included, and normalize to the busiest bucket", () => {
      create();
      const bars = component.activityHistogram();

      expect(bars).toHaveLength(32);
      expect(Math.max(...bars)).toBe(1);
      expect(bars.every((bar) => bar >= 0 && bar <= 1)).toBe(true);
      // Two distinct block times on record (two fixtures share one), so two buckets carry a bar.
      expect(bars.filter((bar) => bar > 0)).toHaveLength(2);
      expect(component.restrictionsInRange()).toBe(3);
    });

    it("should bucket lock times alongside the block times", () => {
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
          locked_at: hoursAgo(4),
          error_message: null
        }
      ]);
      create();

      // Two block buckets plus the lock's own bucket, and the lock counts towards the in-range total.
      expect(component.activityHistogram().filter((bar) => bar > 0)).toHaveLength(3);
      expect(component.restrictionsInRange()).toBe(4);
    });

    it("should render one element per bucket and the range summary ending at now", () => {
      create();
      expect(fixture.nativeElement.querySelectorAll(".ca-activity-bar")).toHaveLength(32);
      expect(component.rangeSummaryTo()).toBe("now");
      expect(fixture.nativeElement.textContent).toContain("3 in range");
    });

    it("should narrow the counted blocks and the highlights when the start thumb moves in", () => {
      create();
      // Half way in: the window starts a day back, so the older entries drop out of the selection.
      component.onRangeStartInput(99);
      fixture.detectChanges();

      expect(component.restrictionsInRange()).toBe(0);
      expect(component.summary().highlights).toEqual([]);
      expect(fixture.nativeElement.textContent).toContain(
        "No IP is blocked and no user locked in the selected time range."
      );
    });

    it("should keep the thumbs from crossing", () => {
      create();
      component.onRangeEndInput(40);
      component.onRangeStartInput(80);
      expect(component.rangeStart()).toBe(40);

      component.onRangeEndInput(10);
      expect(component.rangeEnd()).toBe(40);
    });

    it("should move only the start of the window for a start preset", () => {
      create();
      const end = component.windowEndMs();
      component.applyStartPreset({ label: "Last 24 hours", ageMs: 86_400_000 });

      expect(component.windowEndMs()).toBe(end);
      expect(end - component.windowStartMs()).toBeCloseTo(86_400_000, -3);
      // The selection is reset to the whole new window.
      expect(component.rangeStart()).toBe(0);
      expect(component.rangeEnd()).toBe(100);
    });

    it("should reach back to the oldest recorded block for the open start preset", () => {
      create();
      component.applyStartPreset({ label: "All recorded blocks", ageMs: null });

      // The oldest fixture was blocked five hours ago.
      expect(component.windowEndMs() - component.windowStartMs()).toBeCloseTo(5 * MS_PER_HOUR, -4);
    });

    it("should move only the end of the window for an end preset, and label it with a date", () => {
      create();
      // A start far enough back that the new end does not have to drag it along.
      component.windowStartMs.set(Date.now() - 30 * 86_400_000);
      const start = component.windowStartMs();
      component.applyEndPreset({ label: "Up to 24 hours ago", ageMs: 86_400_000 });
      fixture.detectChanges();

      expect(component.windowStartMs()).toBe(start);
      expect(component.rangeSummaryTo()).not.toBe("now");
      // Everything on record is younger than the new end, so nothing is left in range.
      expect(component.restrictionsInRange()).toBe(0);
    });

    it("should drag the other end along rather than let a preset invert the window", () => {
      create();
      component.applyEndPreset({ label: "Up to 7 days ago", ageMs: 7 * 86_400_000 });
      component.applyStartPreset({ label: "Last 24 hours", ageMs: 86_400_000 });

      expect(component.windowEndMs()).toBeGreaterThan(component.windowStartMs());
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
