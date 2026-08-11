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
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { MatMenu, MatMenuItem, MatMenuTrigger } from "@angular/material/menu";
import { MatSliderModule } from "@angular/material/slider";
import { MatTooltip } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
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
  ConditionalAccessStateService,
  ConditionalAccessStateServiceInterface,
  LockedUsersPage
} from "@services/conditional-access-state/conditional-access-state.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  LockoutPolicy
} from "@services/conditional-access/conditional-access-policy.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { formatLocalDateTime } from "@utils/date-format.utils";
import { forkJoin, of } from "rxjs";

// How many lock records are read for the list. Everything in force is listed, so this is only the ceiling past which
// the widget defers to the locked-users page (and says so in its footer).
const LOCK_RECORD_LIMIT = 100;

const MS_PER_DAY = 86_400_000;
// The range slider's resolution: a fixed number of positions spread over the (dynamic) window.
const SLIDER_STEPS = 100;
// Bars drawn behind the slider, bucketing the window.
const ACTIVITY_BINS = 32;
// Window fallback until the blocklist has loaded (or when it holds no entry to date the window from).
const DEFAULT_WINDOW_MS = 30 * MS_PER_DAY;

// Presets on the icon button at each end of the slider: each one moves only its own end of the window, expressed as
// an age relative to now (0 = now, null = as far back as the data goes).
export interface RangePreset {
  label: string;
  ageMs: number | null;
}

export const WINDOW_START_PRESETS: readonly RangePreset[] = [
  { label: $localize`Everything on record`, ageMs: null },
  { label: $localize`Last 30 days`, ageMs: 30 * MS_PER_DAY },
  { label: $localize`Last 7 days`, ageMs: 7 * MS_PER_DAY },
  { label: $localize`Last 24 hours`, ageMs: MS_PER_DAY }
];

export const WINDOW_END_PRESETS: readonly RangePreset[] = [
  { label: $localize`Up to now`, ageMs: 0 },
  { label: $localize`Up to 24 hours ago`, ageMs: MS_PER_DAY },
  { label: $localize`Up to 7 days ago`, ageMs: 7 * MS_PER_DAY }
];

// The three areas the widget summarizes are governed by separate rights, so each is fetched only when its own
// right is granted and left out of the summary otherwise (see ConditionalAccessSummary's nullable sections).
const POLICY_READ: PolicyAction = "lockout_policy_read";
const LOCKOUT_READ: PolicyAction = "user_lockout_read";
const BLOCKLIST_READ: PolicyAction = "blocklist_read";

// What one request returns per area, with null standing for "not fetched because the right is missing".
interface ConditionalAccessResponses {
  policies: PiResponse<LockoutPolicy[]> | null;
  permanentLocks: PiResponse<LockedUsersPage> | null;
  temporaryLocks: PiResponse<LockedUsersPage> | null;
  expiredLocks: PiResponse<LockedUsersPage> | null;
  recentLocks: PiResponse<LockedUsersPage> | null;
  blocklist: PiResponse<BlocklistEntry[]> | null;
}

// One row of the highlights list: a blocked IP or a locked user, reduced to what the row shows. `at` is when the
// restriction was imposed (the sort key and what the range filter tests), `link` where the row leads.
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

// One record set split by state. `inForce` (permanent + temporary) is what actually restricts access right now;
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
    MatIconButton,
    MatMenu,
    MatMenuItem,
    MatMenuTrigger,
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
  static override readonly requiredAction = [POLICY_READ, LOCKOUT_READ, BLOCKLIST_READ];
  static override readonly title = $localize`Conditional Access`;
  static override readonly icon = "security";
  static override readonly titleLink = ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS;
  // Tall by default: the count rows and the highlights below them only pay off when they are visible at once.
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 11 };
  static override readonly minSize: WidgetSize = { cols: 6, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: 16, rows: 12 };

  protected readonly routePaths = ROUTE_PATHS;

  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  private readonly stateService: ConditionalAccessStateServiceInterface = inject(ConditionalAccessStateService);
  private readonly authenticationLogService: AuthenticationLogServiceInterface = inject(AuthenticationLogService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<ConditionalAccessResponses> | null>(null);
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
      // Every restriction still in force that was imposed inside the selected range - blocked IPs and locked users in
      // one list, most recent first. Expired rows are left to the blocklist / locked-users pages, where they get
      // purged.
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

  readonly sliderSteps = SLIDER_STEPS;

  // When restrictions were imposed: every block on record, whatever its state, plus the locks the highlights page
  // carries. The histogram is about when they were imposed, not about which of them still bite. Locks are limited to
  // that page, so an older lock outside it is not charted.
  private readonly restrictionTimes = computed<number[]>(() => {
    const responses = this.dataRef()?.value();
    return [
      ...(responses?.blocklist?.result?.value ?? []).map((entry) => entry.blocked_at),
      ...(responses?.recentLocks?.result?.value?.locked_users ?? []).map((entry) => entry.locked_at)
    ]
      .map((timestamp) => new Date(timestamp).getTime())
      .filter((time) => !Number.isNaN(time));
  });

  // A "now" sampled once per load, so the window maths and the bar positions read a stable present.
  private readonly nowMs = computed(() => {
    this.dataRef()?.value();
    return Date.now();
  });

  // The window the slider spans: from the oldest recorded block (at least a day back) up to now, until a preset
  // moves either end. Writable, so dragging the thumbs narrows the selection without re-zooming the window.
  readonly windowStartMs = linkedSignal(() => {
    const times = this.restrictionTimes();
    const end = this.nowMs();
    return times.length ? Math.min(end - MS_PER_DAY, Math.min(...times)) : end - DEFAULT_WINDOW_MS;
  });
  readonly windowEndMs = linkedSignal(() => this.nowMs());

  // Thumb positions (0 = window start, SLIDER_STEPS = window end); reset to the full window whenever it moves.
  readonly rangeStart = linkedSignal<number, number>({
    source: () => this.windowStartMs() + this.windowEndMs(),
    computation: () => 0
  });
  readonly rangeEnd = linkedSignal<number, number>({
    source: () => this.windowStartMs() + this.windowEndMs(),
    computation: () => SLIDER_STEPS
  });

  readonly selectedFromMs = computed(() => this.positionToMs(this.rangeStart()));
  readonly selectedToMs = computed(() => this.positionToMs(this.rangeEnd()));

  // Bars behind the slider: the recorded restrictions bucketed across the window, normalized to the busiest bucket.
  readonly activityHistogram = computed<number[]>(() => {
    const bins = new Array<number>(ACTIVITY_BINS).fill(0);
    const start = this.windowStartMs();
    const span = Math.max(1, this.windowEndMs() - start);
    for (const time of this.restrictionTimes()) {
      const fraction = (time - start) / span;
      if (fraction < 0 || fraction > 1) {
        continue;
      }
      bins[Math.min(ACTIVITY_BINS - 1, Math.floor(fraction * ACTIVITY_BINS))]++;
    }
    const max = Math.max(1, ...bins);
    return bins.map((count) => count / max);
  });

  // How many restrictions were imposed inside the selected range, so the histogram carries a number and not just a
  // shape.
  readonly restrictionsInRange = computed<number>(
    () => this.restrictionTimes().filter((time) => time >= this.selectedFromMs() && time <= this.selectedToMs()).length
  );

  readonly startPresets = WINDOW_START_PRESETS;
  readonly endPresets = WINDOW_END_PRESETS;

  readonly rangeSummaryFrom = computed(() => this.summaryFormat(this.selectedFromMs()));
  readonly rangeSummaryTo = computed(() =>
    this.rangeEnd() === SLIDER_STEPS && this.windowEndMs() >= this.nowMs()
      ? $localize`now`
      : this.summaryFormat(this.selectedToMs())
  );

  // Move one end of the window. A preset with no age reaches back to the oldest recorded block; the ends never cross,
  // so picking a start inside the current end (or the other way round) drags the other end along.
  applyStartPreset(preset: RangePreset): void {
    const start = preset.ageMs === null ? this.oldestRestrictionMs() : this.nowMs() - preset.ageMs;
    this.windowStartMs.set(start);
    if (this.windowEndMs() <= start) {
      this.windowEndMs.set(this.nowMs());
    }
  }

  applyEndPreset(preset: RangePreset): void {
    const end = this.nowMs() - (preset.ageMs ?? 0);
    this.windowEndMs.set(end);
    if (this.windowStartMs() >= end) {
      this.windowStartMs.set(end - MS_PER_DAY);
    }
  }

  onRangeStartInput(position: number): void {
    this.rangeStart.set(Math.min(position, this.rangeEnd()));
  }

  onRangeEndInput(position: number): void {
    this.rangeEnd.set(Math.max(position, this.rangeStart()));
  }

  formatSliderThumb = (position: number): string => this.summaryFormat(this.positionToMs(position));

  private oldestRestrictionMs(): number {
    const times = this.restrictionTimes();
    return times.length ? Math.min(...times) : this.nowMs() - DEFAULT_WINDOW_MS;
  }

  private positionToMs(position: number): number {
    const start = this.windowStartMs();
    return start + ((this.windowEndMs() - start) * position) / SLIDER_STEPS;
  }

  private summaryFormat(ms: number): string {
    // Drop the time of day once the window spans more than a day, where it is noise at this width.
    const pattern = this.windowEndMs() - this.windowStartMs() > MS_PER_DAY ? "yyyy-MM-dd" : "yyyy-MM-dd HH:mm";
    return formatDate(ms, pattern, "en-US");
  }

  private inSelectedRange(isoTimestamp: string): boolean {
    const time = new Date(isoTimestamp).getTime();
    return Number.isNaN(time) || (time >= this.selectedFromMs() && time <= this.selectedToMs());
  }

  // Stale rows across both areas: they restrict nobody, but they are what the purge actions on the
  // locked-users and blocklist pages clean up, so the widget names them in one place.
  readonly staleRecords = computed<number>(() => {
    const summary = this.summary();
    return (summary.lockedUsers?.expired ?? 0) + (summary.blockedIps?.expired ?? 0);
  });

  // The restrictions in force the list does not carry: those outside the selected range, and any beyond
  // LOCK_RECORD_LIMIT. Named in the footer, so the list is never mistaken for the whole picture.
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

  ngOnInit(): void {
    const canReadPolicies = this.authService.actionAllowed(POLICY_READ);
    const canReadLockouts = this.authService.actionAllowed(LOCKOUT_READ);
    const canReadBlocklist = this.authService.actionAllowed(BLOCKLIST_READ);
    if (!canReadPolicies && !canReadLockouts && !canReadBlocklist) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(
      this.store.load<ConditionalAccessResponses>("dashboard:conditional-access", () =>
        forkJoin({
          policies: canReadPolicies ? this.policyService.getPolicies() : of(null),
          // The lock counts come per state rather than from one page of records: the totals must cover every
          // lock, not just the page the widget could show.
          permanentLocks: canReadLockouts ? this.stateService.countLockedUsers(["permanent"]) : of(null),
          temporaryLocks: canReadLockouts ? this.stateService.countLockedUsers(["temporary"]) : of(null),
          expiredLocks: canReadLockouts ? this.stateService.countLockedUsers(["expired"]) : of(null),
          // Expired entries are included so the widget can report the stale rows a purge would remove.
          // The records behind the list: the locks still in force, so a lock is listed next to a blocked IP. The
          // counts above stay exact regardless of how many records this page holds.
          recentLocks: canReadLockouts ? this.stateService.fetchLockedUsers(["permanent", "temporary"], LOCK_RECORD_LIMIT) : of(null),
          blocklist: canReadBlocklist ? this.stateService.fetchBlocklist(true) : of(null)
        })
      )
    );
  }

  // Where a highlight row leads: an IP to its own events in the authentication log (the filter is pre-seeded in
  // highlightClicked), a locked user to the locked-users page.
  highlightLink(entry: RestrictionHighlight): string {
    return entry.kind === "ip" ? ROUTE_PATHS.AUTHENTICATION_LOG : ROUTE_PATHS.LOCKED_USERS;
  }

  // Pre-seed the authentication-log filter with a highlighted IP so the log opens on that IP's events only,
  // mirroring the blocklist page. The navigation itself is the template's routerLink.
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

  // A restriction in force is what an admin needs to notice, so any non-zero count is flagged; zero reads as
  // "nobody is currently locked out or blocked".
  protected restrictionClass(count: number): string {
    return count > 0 ? "highlight-false" : "highlight-true";
  }

  private policySummary(policies: LockoutPolicy[]): PolicySummary {
    // A dry-run policy is counted on its own and never as enforcing: it evaluates and records findings, but
    // its actions never run, so an admin reading "3 enforcing" must not be counting it.
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
