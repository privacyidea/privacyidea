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
import { formatDate } from "@angular/common";
import { Component, computed, effect, inject, linkedSignal, OnInit, signal } from "@angular/core";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatIcon } from "@angular/material/icon";
import { MatSliderModule } from "@angular/material/slider";
import { MatTooltip } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import { ACTIVITY_RANGES, ActivityRange } from "@components/dashboard/widgets/activity-range";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import {
  AuthenticationLogService,
  AuthenticationLogServiceInterface
} from "@services/authentication-log/authentication-log.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { PolicyAction } from "@services/auth/policy-actions";
import {
  BlocklistEntry,
  ConditionalAccessOutcomeStatistics,
  ConditionalAccessStateService,
  ConditionalAccessStateServiceInterface,
  LockedUsersPage
} from "@services/conditional-access-state/conditional-access-state.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  ConditionalAccessPolicy
} from "@services/conditional-access/conditional-access-policy.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { formatLocalDateTime } from "@utils/date-format.utils";
import { forkJoin, Observable, of } from "rxjs";

// Cap on how many lock records the widget fetches for the list; beyond it the widget defers to the locked-users page,
// as its footer states.
const LOCK_RECORD_LIMIT = 100;

// The actions that create a restriction, which is what the histogram charts. EMAIL_* and DENY are outcomes too, but
// neither locks anyone: an email notifies, and DENY decides the one request it was evaluated for.
const RESTRICTION_ACTIONS = ["LOCK_USER", "PERMANENT_LOCK_USER", "BLOCK_IP", "PERMANENT_BLOCK_IP"] as const;

// Each of the three areas the widget summarizes has its own read right, so it is fetched only when granted and left out
// of the summary otherwise (see ConditionalAccessSummary's nullable sections).
const POLICY_READ: PolicyAction = "conditional_access_policy_read";
const USER_LOCK_READ: PolicyAction = "user_lock_read";
const BLOCKLIST_READ: PolicyAction = "blocklist_read";
// The outcome history hangs off the authentication-log entries that caused it, so it is read under the log's right
// rather than under any of the three above - an admin may hold those and not this, and then simply gets no history.
const LOG_READ: PolicyAction = "authentication_log_read";

// What one request returns per area, with null standing for "not fetched because the right is missing".
interface ConditionalAccessResponses {
  policies: PiResponse<ConditionalAccessPolicy[]> | null;
  permanentLocks: PiResponse<LockedUsersPage> | null;
  temporaryLocks: PiResponse<LockedUsersPage> | null;
  expiredLocks: PiResponse<LockedUsersPage> | null;
  recentLocks: PiResponse<LockedUsersPage> | null;
  blocklist: PiResponse<BlocklistEntry[]> | null;
  outcomes: PiResponse<ConditionalAccessOutcomeStatistics> | null;
}

// One row of the highlights list: a blocked IP or a locked user, reduced to what the row shows. `at` is when the
// restriction was imposed, both the sort key and what the range filter tests; `kind` decides where the row links (see
// highlightLink).
export interface RestrictionHighlight {
  label: string;
  permanent: boolean;
  at: string;
  expiresAt: string | null;
  kind: "ip" | "user";
}

export interface PolicySummary {
  total: number;
  enforcing: number;
  dryRun: number;
  disabled: number;
}

// One record set split by state: `inForce` (permanent + temporary) is what actually restricts access right now, while
// `expired` rows no longer do and are what the pages' purge action removes.
export interface StateSummary {
  permanent: number;
  temporary: number;
  expired: number;
  inForce: number;
}

export interface ConditionalAccessSummary {
  policies: PolicySummary | null;
  lockedUsers: StateSummary | null;
  blockedIps: StateSummary | null;
  highlights: RestrictionHighlight[];
}

function countOf(response: PiResponse<LockedUsersPage> | null): number {
  return response?.result?.value?.count ?? 0;
}

function isExpired(entry: BlocklistEntry): boolean {
  return !entry.permanent && (entry.seconds_remaining ?? 0) === 0;
}

@Component({
  selector: "app-conditional-access-widget",
  standalone: true,
  imports: [
    InfoHintComponent,
    MatIcon,
    MatButtonToggleModule,
    MatSliderModule,
    MatTooltip,
    RouterLink,
    WidgetStateComponent
  ],
  templateUrl: "./conditional-access-widget.component.html",
  styleUrl: "./conditional-access-widget.component.scss"
})
export class ConditionalAccessWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "conditional-access";
  static override readonly requiredAction = [POLICY_READ, USER_LOCK_READ, BLOCKLIST_READ];
  static override readonly title = $localize`Conditional Access Enforcements`;
  static override readonly icon = "security";
  static override readonly titleLink = ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS;
  static override readonly titleLinkAction = POLICY_READ;
  // Tall by default: the count rows and the highlights below them only pay off when they are visible at once.
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 11 };
  static override readonly minSize: WidgetSize = { cols: 6, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: 16, rows: 12 };

  protected readonly routePaths = ROUTE_PATHS;

  protected readonly ranges = ACTIVITY_RANGES;
  // Which window the history is read over. The same four presets the authentication-activity widget offers, from the
  // same table, so the two charts are read the same way and mean the same thing by "7 d".
  readonly selectedRange = signal<ActivityRange>(ACTIVITY_RANGES[3]);

  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  private readonly stateService: ConditionalAccessStateServiceInterface = inject(ConditionalAccessStateService);
  private readonly authenticationLogService: AuthenticationLogServiceInterface = inject(AuthenticationLogService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<ConditionalAccessResponses> | null>(null);
  // The store key currently in use, so the previous range's entry can be dropped when the range changes.
  private storeKey: string | null = null;
  override readonly partialLoading = computed(() => this.dataRef()?.revalidating() ?? false);
  override readonly refreshFailed = computed(() => {
    const ref = this.dataRef();
    return !!ref && ref.error() && ref.value() !== undefined;
  });

  readonly summary = computed<ConditionalAccessSummary>(() => {
    const responses = this.dataRef()?.value();
    const entries = responses?.blocklist?.result?.value ?? [];
    const enforced = entries.filter((entry) => !isExpired(entry));

    return {
      policies: responses?.policies ? this.policySummary(responses.policies.result?.value ?? []) : null,
      lockedUsers: responses?.permanentLocks
        ? {
            permanent: countOf(responses.permanentLocks),
            temporary: countOf(responses.temporaryLocks),
            expired: countOf(responses.expiredLocks),
            inForce: countOf(responses.permanentLocks) + countOf(responses.temporaryLocks)
          }
        : null,
      blockedIps: responses?.blocklist
        ? {
            permanent: entries.filter((entry) => entry.permanent).length,
            temporary: enforced.filter((entry) => !entry.permanent).length,
            expired: entries.length - enforced.length,
            inForce: enforced.length
          }
        : null,
      // Every restriction still in force and imposed inside the selected range, blocked IPs and locked users combined
      // into one most-recent-first list; expired rows are left for the blocklist / locked-users pages to purge.
      highlights: [
        ...enforced.map<RestrictionHighlight>((entry) => ({
          label: entry.identifier,
          permanent: entry.permanent,
          at: entry.blocked_at,
          expiresAt: entry.block_expires_at,
          kind: "ip"
        })),
        ...(responses?.recentLocks?.result?.value?.locked_users ?? []).map<RestrictionHighlight>((entry) => ({
          label: entry.realm ? `${entry.username}@${entry.realm}` : entry.username,
          permanent: entry.permanent,
          at: entry.locked_at,
          expiresAt: entry.lock_expires_at,
          kind: "user"
        }))
      ]
        .filter((entry) => this.inSelectedRange(entry.at))
        .sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0))
    };
  });

  // --- Blocklist activity over time ---

  // When restrictions were imposed, bucketed by the server: one count per bucket, summed across the actions that
  // create a restriction.
  //
  // Read from the conditional-access outcome history rather than from the live lock and block state, which is what
  // this widget's numbers above are. Those two answer different questions: the state says who is restricted *now* and
  // forgets a lock once it lapses, while an outcome row survives the lock expiring, being reset or being purged - so
  // this is a history rather than a picture of the present, which is what a "when did this happen" chart has to be.
  //
  // Not the log's own event types either: USER_LOCKED there is a request a lock already in force turned away, so
  // charting those would count the retries against one lock instead of the lock.
  private readonly restrictionCounts = computed<number[]>(() => {
    const statistics = this.dataRef()?.value()?.outcomes?.result?.value;
    if (!statistics) {
      return [];
    }
    const bins = new Array<number>(statistics.bins.count).fill(0);
    for (const series of statistics.outcomes) {
      series.counts.forEach((count, index) => (bins[index] += count));
    }
    return bins;
  });

  // How many buckets the response holds, which is also the brush's resolution: a thumb steps from one bucket edge to
  // the next, because whole buckets are the finest cut the fetched counts can answer for - the same brush the
  // authentication-activity chart carries.
  readonly binCount = computed<number>(() => this.restrictionCounts().length);

  // The bucket edges the counts are bucketed by, so a brushed span can be turned back into buckets.
  private readonly binStartsMs = computed<number[]>(
    () =>
      this.dataRef()
        ?.value()
        ?.outcomes?.result?.value?.bins?.starts?.map((start) => Date.parse(start)) ?? []
  );

  // Where the fetched window closes, which is what the edge past the last bucket stands for. The window's *start*
  // needs no accessor of its own: the first bucket's start is it, and the labels and the brush both read the bucket
  // edges. Nothing re-zooms this window either - the preset chooses it and the request is cut over it, so a
  // client-side zoom would leave the bars at the fetched resolution while the axis claimed a narrower span.
  private readonly windowEndMs = computed(() => {
    const window = this.dataRef()?.value()?.outcomes?.result?.value?.window;
    return window ? Date.parse(window.end_time) : Date.now();
  });

  // What makes a brush stale: the window it was drawn over, and the buckets its thumbs step through. Deliberately not
  // the response itself - a refresh of the same window keeps the reader's span instead of snapping it open, while a
  // new preset, whose window the old positions would name a different span of, opens it.
  private readonly brushBasis = computed(() => `${this.selectedRange().id}:${this.binCount()}`);

  // The selection as a half-open span of edges: the buckets rangeStart .. rangeEnd - 1.
  readonly rangeStart = linkedSignal<string, number>({
    source: this.brushBasis,
    computation: () => 0
  });
  readonly rangeEnd = linkedSignal<string, number>({
    source: this.brushBasis,
    computation: () => this.binCount()
  });

  readonly selectedFromMs = computed(() => this.edgeMs(this.rangeStart()));
  readonly selectedToMs = computed(() => this.edgeMs(this.rangeEnd()));

  // Bars behind the slider. The bucketing is the server's, so this only normalizes them to the busiest bucket.
  readonly activityHistogram = computed<number[]>(() => {
    const counts = this.restrictionCounts();
    const max = Math.max(1, ...counts);
    return counts.map((count) => count / max);
  });

  // Whether a bucket is one the brush selects. Drives the bars' muting, so the chart shows which part of the shape
  // the number beside it is counting.
  inSelection(bin: number): boolean {
    return bin >= this.rangeStart() && bin < this.rangeEnd();
  }

  // How many restrictions were imposed inside the selected range, so the histogram carries a number and not just a
  // shape. Summed over the buckets the brush covers: a bucket counts when it starts inside the span, which is the
  // finest the server-side bucketing can answer for.
  // Whether the widget has a history to chart at all: an admin without the log right gets the numbers and the
  // restrictions list, and no "over time" section.
  readonly hasHistory = computed<boolean>(() => !!this.dataRef()?.value()?.outcomes?.result?.value);

  readonly restrictionsInRange = computed<number>(() =>
    this.restrictionCounts()
      .slice(this.rangeStart(), this.rangeEnd())
      .reduce((sum, count) => sum + count, 0)
  );

  // The labels under the brush, which are also what each thumb announces. The window was fetched as "this span up to
  // now", so its own end *is* the present: the top of the slider reads "now" rather than the timestamp the request
  // happened to carry.
  readonly rangeSummaryFrom = computed(() => this.summaryFormat(this.selectedFromMs()));
  readonly rangeSummaryTo = computed(() =>
    this.rangeEnd() >= this.binCount() ? $localize`now` : this.summaryFormat(this.selectedToMs())
  );

  selectRange(id: string): void {
    const range = ACTIVITY_RANGES.find((candidate) => candidate.id === id);
    if (range) {
      this.selectedRange.set(range);
    }
  }

  // The thumbs keep one bucket between them rather than being allowed to meet. A closed brush would select nothing:
  // the count would read zero and the chart would look empty instead of unselected.
  onRangeStartInput(edge: number): void {
    this.rangeStart.set(Math.min(edge, this.rangeEnd() - 1));
  }

  onRangeEndInput(edge: number): void {
    this.rangeEnd.set(Math.max(edge, this.rangeStart() + 1));
  }

  formatSliderThumb = (edge: number): string => this.summaryFormat(this.edgeMs(edge));

  // When a bucket edge falls. The edge past the last bucket is the window's end, there being no bucket after it.
  private edgeMs(edge: number): number {
    return this.binStartsMs()[edge] ?? this.windowEndMs();
  }

  private summaryFormat(ms: number): string {
    // Drop the time of day once a bucket is a whole day, where it is noise at this width.
    const pattern = this.selectedRange().wholeDayBuckets ? "yyyy-MM-dd" : "yyyy-MM-dd HH:mm";
    return formatDate(ms, pattern, "en-US");
  }

  private inSelectedRange(isoTimestamp: string): boolean {
    const time = new Date(isoTimestamp).getTime();
    return Number.isNaN(time) || (time >= this.selectedFromMs() && time <= this.selectedToMs());
  }

  // Stale rows across both areas restrict nobody, but they are what the locked-users and blocklist pages' purge actions
  // clean up, so the widget names them in one place.
  readonly staleRecords = computed<number>(() => {
    const summary = this.summary();
    return (summary.lockedUsers?.expired ?? 0) + (summary.blockedIps?.expired ?? 0);
  });

  // Restrictions in force that the list omits: those outside the selected range, plus any beyond LOCK_RECORD_LIMIT;
  // named in the footer so the list is never mistaken for the whole picture.
  readonly hiddenHighlightCount = computed<number>(() => {
    const summary = this.summary();
    const inForce = (summary.blockedIps?.inForce ?? 0) + (summary.lockedUsers?.inForce ?? 0);
    return Math.max(0, inForce - summary.highlights.length);
  });

  constructor() {
    super();
    effect(() => {
      const ref = this.dataRef();
      if (!ref) {
        return;
      }
      const value = ref.value();
      if (value === undefined) {
        this.state.set(ref.error() ? "error" : "loading");
        return;
      }
      // A skipped area contributes no response, so only the ones actually fetched decide the state.
      const fetched = Object.values(value).filter((response) => response !== null);
      this.state.set(fetched.every((response) => response?.result?.status === true) ? "ready" : "error");
    });
  }

  override reload(): void {
    this.ngOnInit();
  }

  // Refetches whenever the preset changes: the window is the request's, so a new preset is a new request.
  private readonly reloadOnRangeChange = effect(() => {
    this.selectedRange();
    this.ngOnInit();
  });

  ngOnInit(): void {
    const canReadPolicies = this.authService.actionAllowed(POLICY_READ);
    const canReadUserLocks = this.authService.actionAllowed(USER_LOCK_READ);
    const canReadBlocklist = this.authService.actionAllowed(BLOCKLIST_READ);
    const canReadLog = this.authService.actionAllowed(LOG_READ);
    if (!canReadPolicies && !canReadUserLocks && !canReadBlocklist) {
      this.state.set("denied");
      return;
    }
    // Keyed by the selected range, so switching preset fetches that window rather than re-reading the last one; the
    // entry left behind has to go, because DashboardDataStore.refreshAll() refetches every entry it holds and a stale
    // key would keep re-querying a window nobody is looking at.
    const key = `dashboard:conditional-access:${this.selectedRange().id}`;
    if (this.storeKey && this.storeKey !== key) {
      this.store.invalidate(this.storeKey);
    }
    this.storeKey = key;
    this.dataRef.set(
      this.store.load<ConditionalAccessResponses>(key, () =>
        forkJoin({
          policies: canReadPolicies ? this.policyService.getPolicies() : of(null),
          // Lock counts come per state rather than from one page of records, so the totals cover every lock rather than
          // only the page the widget can show.
          permanentLocks: canReadUserLocks ? this.stateService.countLockedUsers(["permanent"]) : of(null),
          temporaryLocks: canReadUserLocks ? this.stateService.countLockedUsers(["temporary"]) : of(null),
          expiredLocks: canReadUserLocks ? this.stateService.countLockedUsers(["expired"]) : of(null),
          // Expired entries are included so the widget can report the stale rows a purge would remove. The records
          // behind the list: locks still in force, listed alongside blocked IPs, while the counts above stay exact
          // regardless of how many records this page holds.
          recentLocks: canReadUserLocks
            ? this.stateService.fetchLockedUsers(["permanent", "temporary"], LOCK_RECORD_LIMIT)
            : of(null),
          blocklist: canReadBlocklist ? this.stateService.fetchBlocklist(true) : of(null),
          // The window is computed per invocation, not once when the factory is registered:
          // DashboardDataStore.refreshAll() replays the stored factory, and a captured window would make every later
          // refresh ask for the same stale one.
          outcomes: canReadLog ? this.fetchHistory() : of(null)
        })
      )
    );
  }

  private fetchHistory(): Observable<PiResponse<ConditionalAccessOutcomeStatistics>> {
    const window = this.selectedRange().window(new Date());
    return this.stateService.fetchOutcomeStatistics(
      window.start.toISOString(),
      window.end.toISOString(),
      window.bins,
      RESTRICTION_ACTIONS
    );
  }

  // Where a highlight row leads: an IP to its own events in the authentication log (filter pre-seeded in
  // highlightClicked), a locked user to the locked-users page.
  highlightLink(entry: RestrictionHighlight): string {
    return entry.kind === "ip" ? ROUTE_PATHS.AUTHENTICATION_LOG : ROUTE_PATHS.LOCKED_USERS;
  }

  // Pre-seeds the authentication-log filter with a highlighted IP so the log opens on just that IP's events, mirroring
  // the blocklist page; the template's routerLink handles the navigation itself.
  highlightClicked(entry: RestrictionHighlight): void {
    if (entry.kind === "ip") {
      this.authenticationLogService.authenticationLogFilter.set(new FilterValue().addEntry("source_ip", entry.label));
    }
  }

  highlightTooltip(entry: RestrictionHighlight): string {
    if (entry.kind === "ip") {
      return $localize`Blocked ${formatLocalDateTime(entry.at)} - show this IP's authentication log`;
    }
    return $localize`Locked ${formatLocalDateTime(entry.at)} - show the locked users`;
  }

  expiresTooltip(entry: RestrictionHighlight): string {
    return $localize`In force until ${formatLocalDateTime(entry.expiresAt)}`;
  }

  // A restriction in force is what an admin needs to notice, so any non-zero count is flagged, while zero reads as
  // "nobody is currently locked out or blocked".
  protected restrictionClass(count: number): string {
    return count > 0 ? "highlight-false" : "highlight-true";
  }

  private policySummary(policies: ConditionalAccessPolicy[]): PolicySummary {
    // A dry-run policy is counted on its own, never as enforcing: it evaluates and records findings, but its actions
    // never run, so "3 enforcing" must not include it.
    const enabled = policies.filter((policy) => policy.enabled);
    const dryRun = enabled.filter((policy) => policy.dry_run);
    return {
      total: policies.length,
      enforcing: enabled.length - dryRun.length,
      dryRun: dryRun.length,
      disabled: policies.length - enabled.length
    };
  }
}
