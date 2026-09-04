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
import { Component, computed, effect, inject, signal, TemplateRef, viewChild } from "@angular/core";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import {
  AuthenticationEventSeries,
  AuthenticationLogService,
  AuthenticationLogServiceInterface,
  AuthenticationLogStatistics
} from "@services/authentication-log/authentication-log.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { PolicyAction } from "@services/auth/policy-actions";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { toFilterDisplay } from "@utils/date-format.utils";

const LOG_READ: PolicyAction = "authentication_log_read";

// Bins are chosen per range so a bucket is a round unit of time - hourly for a day, six-hourly for a week, daily for a
// month - rather than an arbitrary slice.
export interface ActivityRange {
  label: string;
  hours: number;
  bins: number;
}

export const ACTIVITY_RANGES: readonly ActivityRange[] = [
  { label: $localize`1 h`, hours: 1, bins: 12 },
  { label: $localize`24 h`, hours: 24, bins: 24 },
  { label: $localize`7 d`, hours: 168, bins: 28 },
  { label: $localize`30 d`, hours: 720, bins: 30 }
];

// One row of the activity chart: a single outcome's attempts per bin. Kept as separate rows rather than one stacked
// bar because the theme's success and failure colours are indistinguishable under deuteranopia in dark mode - row
// position and the row's own label carry the identity, and the colour only reinforces it.
export interface ActivityRow {
  label: string;
  outcome: string;
  counts: number[];
  total: number;
  // This outcome's share of every attempt in the window, pending included; null when the window holds none.
  share: number | null;
}

export interface FailureReason {
  eventType: string;
  count: number;
}

export interface ActivitySummary {
  success: number;
  failure: number;
  pending: number;
  rows: ActivityRow[];
  reasons: FailureReason[];
}

@Component({
  selector: "app-authentication-activity-widget",
  standalone: true,
  imports: [InfoHintComponent, MatButtonToggleModule, MatIcon, MatTooltip, RouterLink, WidgetStateComponent],
  templateUrl: "./authentication-activity-widget.component.html",
  styleUrl: "./authentication-activity-widget.component.scss"
})
export class AuthenticationActivityWidgetComponent extends DashboardWidget {
  static override readonly type = "authentication-activity";
  static override readonly requiredAction = LOG_READ;
  static override readonly title = $localize`Authentication Activity`;
  static override readonly icon = "lock";
  static override readonly titleLink = ROUTE_PATHS.AUTHENTICATION_LOG;
  static override readonly titleLinkAction = LOG_READ;
  static override readonly defaultSize: WidgetSize = { cols: 5, rows: 8 };
  static override readonly minSize: WidgetSize = { cols: 4, rows: 7 };
  static override readonly maxSize: WidgetSize = { cols: 12, rows: 12 };

  // Read by the widget frame, which renders these in its header.
  override readonly headerActions = viewChild<TemplateRef<unknown>>("headerActions");

  protected readonly routePaths = ROUTE_PATHS;
  protected readonly ranges = ACTIVITY_RANGES;
  protected readonly info = $localize`Authentication attempts, not single requests: the several log entries of one \
challenge-response login count once, classified by how the attempt ended.`;

  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly authenticationLogService: AuthenticationLogServiceInterface = inject(AuthenticationLogService);
  private readonly store = inject(DashboardDataStore);

  readonly selectedRange = signal<ActivityRange>(ACTIVITY_RANGES[1]);

  private readonly dataRef = signal<DashboardDataRef<PiResponse<AuthenticationLogStatistics>> | null>(null);
  // The store key currently in use, so the previous range's entry can be dropped when the range changes.
  private storeKey: string | null = null;
  override readonly partialLoading = computed(() => this.dataRef()?.revalidating() ?? false);
  override readonly refreshFailed = computed(() => {
    const ref = this.dataRef();
    return !!ref && ref.error() && ref.value() !== undefined;
  });

  private readonly statistics = computed<AuthenticationLogStatistics | null>(
    () => this.dataRef()?.value()?.result?.value ?? null
  );

  readonly binStarts = computed<string[]>(() => this.statistics()?.bins?.starts ?? []);

  // The window's own start, so the axis labels what was actually queried rather than recomputing it. The time is
  // always shown, for the same reason binTooltip shows it: the window is measured back from now rather than snapped
  // to midnight, so a date on its own would claim a calendar day the window only partly covers.
  readonly windowStart = computed<string>(() => {
    const start = this.statistics()?.window?.start_time;
    if (!start) {
      return "";
    }
    return formatDate(start, "yyyy-MM-dd HH:mm", "en-US");
  });

  // The tallest bin across both rows. The rows share it so their heights stay comparable: a failure row scaled to its
  // own peak would make a handful of failures look like an outage.
  readonly peak = computed<number>(() => Math.max(1, ...this.summary().rows.flatMap((row) => row.counts)));

  readonly summary = computed<ActivitySummary>(() => {
    // Every classification the endpoint returns, the ones conditional access writes for its own rejections
    // (USER_LOCKED, IP_BLOCKED, ACCESS_DENIED) included: an attempt it turned away did fail, and naming why is the
    // point of the table below. Note one lock can produce many rejections, so such a reason counts retries rather
    // than locks - the conditional-access widget is where locks themselves are counted.
    const series = this.statistics()?.events ?? [];
    const binCount = this.statistics()?.bins?.count ?? 0;
    const totalOf = (outcome: string) =>
      series.filter((entry) => entry.outcome === outcome).reduce((sum, entry) => sum + entry.total, 0);
    const success = totalOf("success");
    const failure = totalOf("failure");
    const pending = totalOf("pending");
    // Every attempt in the window, pending included: the three shares then add up to the whole, so a row's percentage
    // reads as "this much of what happened" rather than shifting with how many attempts have resolved so far.
    const attempts = success + failure + pending;
    const share = (count: number) => (attempts ? count / attempts : null);
    const reasons = series
      .filter((entry) => entry.outcome === "failure")
      .map((entry) => ({ eventType: entry.event_type, count: entry.total }));

    return {
      success,
      failure,
      pending,
      rows: [
        {
          label: $localize`Successful`,
          outcome: "success",
          counts: this.binsOf(series, "success", binCount),
          total: success,
          share: share(success)
        },
        {
          label: $localize`Failed`,
          outcome: "failure",
          counts: this.binsOf(series, "failure", binCount),
          total: failure,
          share: share(failure)
        },
        {
          // An attempt counts here when its latest event is a challenge or enrolment with no answer logged after
          // it, so a bucket dates when the attempt *started*.
          label: $localize`Pending`,
          outcome: "pending",
          counts: this.binsOf(series, "pending", binCount),
          total: pending,
          share: share(pending)
        }
      ],
      // Already ordered by descending total from the endpoint, so the most common reason leads. The widget body
      // scrolls, so the list is not capped: a cap would need a control to lift it, which costs more room than the
      // rows it saves.
      reasons
    };
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
      this.state.set(value.result?.status === true ? "ready" : "error");
    });
    // Refetches whenever the range changes; the store key carries the range so the ranges do not evict one another
    // and a dashboard-wide refresh reloads the one on screen.
    effect(() => this.load(this.selectedRange()));
  }

  override reload(): void {
    this.load(this.selectedRange());
  }

  selectRange(hours: number): void {
    const range = ACTIVITY_RANGES.find((candidate) => candidate.hours === hours);
    if (range) {
      this.selectedRange.set(range);
    }
  }

  private load(range: ActivityRange): void {
    if (!this.authService.actionAllowed(LOG_READ)) {
      this.state.set("denied");
      return;
    }
    const key = `dashboard:auth-activity:${range.hours}`;
    // Each range needs a key of its own, so switching shows a loading state rather than the previous range's numbers.
    // The entry left behind has to go, though: DashboardDataStore.refreshAll() refetches every entry it holds, so a
    // stale key would keep re-querying a window nobody is looking at on each dashboard refresh.
    if (this.storeKey && this.storeKey !== key) {
      this.store.invalidate(this.storeKey);
    }
    this.storeKey = key;
    this.dataRef.set(
      this.store.load(key, () => {
        // Computed per invocation, not once when the factory is registered: DashboardDataStore.refreshAll() replays
        // the stored factory, and a captured window would make every later refresh ask for the same stale range.
        const end = new Date();
        const start = new Date(end.getTime() - range.hours * 3_600_000);
        return this.authenticationLogService.fetchStatistics(start.toISOString(), end.toISOString(), range.bins);
      })
    );
  }

  // Sums the per-bin counts of every series sharing an outcome, so a row is that outcome's whole volume rather than
  // its most common event type.
  private binsOf(series: AuthenticationEventSeries[], outcome: string, binCount: number): number[] {
    const totals = new Array<number>(binCount).fill(0);
    for (const entry of series.filter((candidate) => candidate.outcome === outcome)) {
      entry.counts.forEach((count, index) => (totals[index] += count));
    }
    return totals;
  }

  barHeight(count: number): number {
    // A non-zero bin keeps a visible sliver, so a quiet bucket and an empty one never look the same.
    return count === 0 ? 0 : Math.max(4, (count / this.peak()) * 100);
  }

  // The span a column covers. The counts are not repeated here: the row already prints its total and the bar heights
  // compare against it, so the tooltip only has to answer "when is this".
  //
  // The time is always shown. Buckets are measured back from now rather than snapped to midnight, so even a bucket a
  // whole day wide runs from something like 08:37 to 08:37 the next day - a date on its own would claim a calendar
  // day the bucket does not cover. The date is printed once when both ends fall on it and twice when the bucket
  // crosses into the next.
  binTooltip(index: number): string {
    const starts = this.binStarts();
    const from = starts[index];
    if (!from) {
      return "";
    }
    const fromDate = formatDate(from, "yyyy-MM-dd", "en-US");
    const fromTime = formatDate(from, "HH:mm", "en-US");
    const to = starts[index + 1] ?? this.statistics()?.window?.end_time;
    if (!to) {
      return `${fromDate} ${fromTime}`;
    }
    const toDate = formatDate(to, "yyyy-MM-dd", "en-US");
    const toTime = formatDate(to, "HH:mm", "en-US");
    return fromDate === toDate
      ? `${fromDate} ${fromTime} – ${toTime}`
      : `${fromDate} ${fromTime} – ${toDate} ${toTime}`;
  }

  shareLabel(row: ActivityRow): string {
    return row.share === null ? "" : `(${Math.round(row.share * 100)}%)`;
  }

  // Opens the log on the attempts behind a row of the reasons table, carrying the window with the filter: the log
  // keeps whatever timestamps it was last left with, so without this the count shown here and the rows listed there
  // could describe different periods.
  //
  // The window goes into the filter *chips* as well as the signals. The log derives its time filter from the chip
  // text and clears a bound whose chip is missing, so setting the signals alone would be undone the moment the page
  // loads. toFilterDisplay is the form the page itself writes, which is what keeps it from reading the chip as an
  // edit and reparsing it.
  showEventType(eventType: string): void {
    const window = this.statistics()?.window;
    let filter = new FilterValue().addEntry("event_type", eventType);
    if (window) {
      filter = filter
        .addEntry("start_time", toFilterDisplay(window.start_time))
        .addEntry("end_time", toFilterDisplay(window.end_time));
    }
    this.authenticationLogService.authenticationLogFilter.set(filter);
    this.authenticationLogService.timestampFrom.set(window?.start_time ?? null);
    this.authenticationLogService.timestampTo.set(window?.end_time ?? null);
  }
}
