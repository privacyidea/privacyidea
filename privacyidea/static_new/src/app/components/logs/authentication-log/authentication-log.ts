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
import { DatePipe, formatDate, NgClass } from "@angular/common";
import {
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { provideNativeDateAdapter } from "@angular/material/core";
import { MatDatepickerModule } from "@angular/material/datepicker";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatMenuModule } from "@angular/material/menu";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
import { MatSliderModule } from "@angular/material/slider";
import {
  MatCell,
  MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow,
  MatHeaderRowDef,
  MatNoDataRow,
  MatRow,
  MatRowDef,
  MatTable,
  MatTableDataSource
} from "@angular/material/table";
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { MultiSelectFilterComponent } from "@components/shared/multi-select-filter/multi-select-filter.component";
import { MultiSelectFilterOption } from "@components/shared/multi-select-filter/multi-select-filter-option";
import { MultiSelectMenuComponent } from "@components/shared/multi-select-filter/multi-select-menu/multi-select-menu.component";
import { USER_AGENT_PRESETS } from "@core/constants/user-agents";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ClientsService, ClientsServiceInterface } from "@services/clients/clients.service";
import {
  AuthenticationLogEntry,
  AuthenticationLogService,
  AuthenticationLogServiceInterface
} from "@services/authentication-log/authentication-log.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

// CSS highlight class per event outcome (defined in styles/table.scss). Outcome values mirror AuthEventOutcome in
// privacyidea/lib/conditional_access/authentication_event_types.py. The event-type list and each type's outcome come
// from the backend (GET /authenticationlog/eventtypes); the WebUI only maps an outcome to its color here.
const OUTCOME_CLASS: Record<string, string> = {
  success: "highlight-true",
  failure: "highlight-false",
  pending: "highlight-warning"
};

// User-identifying columns hidden in self-service: every row is the logged-in user (redundant), and their
// realm/resolver/user links point to admin-only pages.
const USER_SCOPED_COLUMN_KEYS = ["username", "realm", "resolver", "uid"];

// Single source for all user roles: filter-menu label, and badge metadata for admin roles.
// Regular users get no badge (they are the default and appear on almost every row).
const ROLE_CONFIG: readonly {
  value: string;
  filterLabel: string;
  badge?: { label: string; tooltip: string; class: string };
}[] = [
  { value: "user", filterLabel: $localize`User` },
  {
    value: "admin-internal",
    filterLabel: $localize`Internal Admin`,
    badge: {
      label: $localize`internal admin`,
      tooltip: $localize`Local database administrator.`,
      class: "role-badge-admin-internal"
    }
  },
  {
    value: "admin-external",
    filterLabel: $localize`External Admin`,
    badge: {
      label: $localize`external admin`,
      tooltip: $localize`Administrator from an admin realm.`,
      class: "role-badge-admin-external"
    }
  }
];

const USER_ROLE_BADGES: Record<string, { label: string; tooltip: string; class: string }> = Object.fromEntries(
  ROLE_CONFIG.filter((role) => role.badge).map((r) => [r.value, r.badge!])
);

// `sortable` mirrors SORTABLE_COLUMNS in privacyidea/lib/conditional_access/authentication_log.py. Every column is
// sortable except `other_info`, which is a JSON column the backend cannot order on meaningfully.
const columnKeysMap: { key: string; label: string; filterable: boolean; sortable: boolean }[] = [
  // The timestamp filter lives in the table-action row (preset menu + custom-range slider), not in the column header,
  // so the header only offers sorting.
  { key: "timestamp", label: $localize`Timestamp`, filterable: false, sortable: true },
  { key: "event_type", label: $localize`Event Type`, filterable: true, sortable: true },
  { key: "username", label: $localize`User`, filterable: true, sortable: true },
  { key: "realm", label: $localize`Realm`, filterable: true, sortable: true },
  { key: "resolver", label: $localize`Resolver`, filterable: true, sortable: true },
  { key: "uid", label: $localize`UID`, filterable: true, sortable: true },
  { key: "source_ip", label: $localize`Source IP`, filterable: true, sortable: true },
  { key: "client_label", label: $localize`Client`, filterable: true, sortable: true },
  { key: "serial", label: $localize`Serial`, filterable: true, sortable: true },
  { key: "transaction_id", label: $localize`Transaction ID`, filterable: true, sortable: true },
  { key: "previous_transaction_id", label: $localize`Previous Transaction ID`, filterable: true, sortable: true },
  { key: "other_info", label: $localize`Info`, filterable: false, sortable: false }
];

// Local start-of-day / end-of-day ISO bounds for a date chosen in the range picker. The picker yields a native Date
// at local midnight; the log renders timestamps in local time, so the bounds are the local day edges (inclusive end
// at 23:59:59) converted to the ISO the API filter expects.
function startOfDayIso(date: Date): string {
  const day = new Date(date);
  day.setHours(0, 0, 0, 0);
  return day.toISOString();
}

function endOfDayIso(date: Date): string {
  const day = new Date(date);
  day.setHours(23, 59, 59, 0);
  return day.toISOString();
}

// The custom-range slider has a fixed number of positions (its resolution); the time span they cover is dynamic (the
// window). It defaults to the span from the oldest entry to now, or the widest fallback until that loads.
const RANGE_SLIDER_STEPS = 200;
const MS_PER_DAY = 86_400_000;
const DEFAULT_SLIDER_WINDOW_MS = 365 * MS_PER_DAY;

// "Last X" spans and their labels for the date-range button: when the active range ends at ~now and its duration
// matches one of these (within tolerance), the button shows that friendly period name instead of "Custom range".
const PRESET_LABELS: readonly { ms: number; label: string }[] = [
  { ms: MS_PER_DAY, label: $localize`Last 24 hours` },
  { ms: 7 * MS_PER_DAY, label: $localize`Last 7 days` },
  { ms: 30 * MS_PER_DAY, label: $localize`Last 30 days` },
  { ms: 90 * MS_PER_DAY, label: $localize`Last 3 months` },
  { ms: 182 * MS_PER_DAY, label: $localize`Last 6 months` },
  { ms: 365 * MS_PER_DAY, label: $localize`Last year` }
];

// Converts an ISO 8601 string to the human-readable format shown in the active-filter chip.
// Input: ISO 8601, e.g. "2026-06-02T10:00:00.000Z". Output: "2026-06-02 10:00:00 +00:00".
function toFilterDisplay(isoString: string): string {
  return formatDate(isoString, "yyyy-MM-dd HH:mm:ss ZZZZZ", "en-US");
}

// Inverse of toFilterDisplay for the editable start_time/end_time chips: parse the mirrored display, plain ISO, or a
// partial datetime the user typed into an ISO string. Returns null for an empty or unparsable value.
function parseFilterTimestamp(value: string | null | undefined): string | null {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    return null;
  }
  // Normalize the mirrored "yyyy-MM-dd HH:mm:ss +00:00" form to ISO (space->T, drop the space before the offset),
  // then fall back to the raw text so plain ISO input still parses.
  for (const candidate of [trimmed.replace(" ", "T").replace(/\s+(?=[+\-Z])/, ""), trimmed]) {
    const date = new Date(candidate);
    if (!isNaN(date.getTime())) {
      return date.toISOString();
    }
  }
  return null;
}

// Full, independently-translatable tooltip per column that has an inline filter button. Kept as complete sentences
// (not noun-interpolated) so each language can phrase determiner/grammar correctly; a column without an entry falls
// back to the button's generic default.
const FILTER_TOOLTIPS: Record<string, string> = {
  username: $localize`Filter by this user`,
  resolver: $localize`Filter by this resolver`,
  uid: $localize`Filter by this UID`,
  source_ip: $localize`Filter by this source IP`,
  serial: $localize`Filter by this serial`,
  transaction_id: $localize`Filter by this transaction ID`,
  previous_transaction_id: $localize`Filter by this previous transaction ID`
};

// A rendered other_info row: a leaf carries `value`; a one-level-nested dict carries `children` (rendered as a
// sub-list) instead. Nesting deeper than one level is folded into the leaf value as compact JSON.
interface InfoEntry {
  key: string;
  value?: string;
  children?: { key: string; value: string }[];
}

@Component({
  selector: "app-authentication-log",
  imports: [
    MatCell,
    MatFormField,
    MatHint,
    MatInput,
    MatPaginator,
    MatHeaderCellDef,
    MatHeaderCell,
    MatTable,
    MatCellDef,
    NgClass,
    MatHeaderRowDef,
    MatHeaderRow,
    MatRowDef,
    MatNoDataRow,
    MatRow,
    MatColumnDef,
    MatLabel,
    CopyableComponent,
    FilterValueButtonComponent,
    RouterLink,
    ScrollToTopDirective,
    ScrollEdgesDirective,
    DatePipe,
    ClearableInputComponent,
    MultiSelectFilterComponent,
    MultiSelectMenuComponent,
    MatIcon,
    MatButtonModule,
    MatDatepickerModule,
    MatIconModule,
    MatMenuModule,
    MatSliderModule,
    MatTooltipModule
  ],
  providers: [provideNativeDateAdapter()],
  templateUrl: "./authentication-log.html",
  styleUrl: "./authentication-log.scss"
})
export class AuthenticationLog {
  readonly columnKeysMap = columnKeysMap;
  // Cells whose content can grow tall (stacked serials, long JSON) get a capped, scrollable cell.
  readonly scrollableColumnKeys = ["serial", "other_info"];
  // Client filter: show the friendly user-agent name, filter by its identifier prefix (a trailing "*" is applied by
  // the multi-select component since client_label stores the full user-agent string incl. version).
  // REVIEW: once selected, the shared filter input shows the raw stored value (e.g. `client_label: privacyIDEA-Keycloak*`)
  // rather than the friendly name the user picked; consider mapping it back for display.
  readonly clientLabelOptions: readonly MultiSelectFilterOption[] = USER_AGENT_PRESETS.map((preset) => ({
    label: preset.displayName,
    value: preset.identifier
  }));
  // user_role has no table column (it is "user" on almost every row); it is filtered via the "More Filter" menu.
  readonly userRoleOptions: readonly MultiSelectFilterOption[] = ROLE_CONFIG.map((role) => ({
    label: role.filterLabel,
    value: role.value
  }));
  protected readonly authenticationLogService: AuthenticationLogServiceInterface = inject(AuthenticationLogService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly clientsService: ClientsServiceInterface = inject(ClientsService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  sort = this.authenticationLogService.sort;

  readonly eventTypeOptions = computed<string[]>(() =>
    this.authenticationLogService.eventTypes().map((entry) => entry.name)
  );
  private readonly outcomeByEventType = computed<Map<string, string>>(
    () => new Map(this.authenticationLogService.eventTypes().map((entry) => [entry.name, entry.outcome]))
  );

  // Columns to render: a self-service user only ever sees their own entries, so the user-identifying columns are
  // hidden (redundant, and their realm/resolver/user links target admin-only pages).
  readonly visibleColumns = computed(() =>
    this.authService.isSelfServiceUser()
      ? this.columnKeysMap.filter((column) => !USER_SCOPED_COLUMN_KEYS.includes(column.key))
      : this.columnKeysMap
  );
  readonly visibleColumnKeys = computed(() => this.visibleColumns().map((column) => column.key));

  // Source-IP filter options come from the known clients (requires the `clienttype` right, hence may be empty). IPs
  // match exactly and display == value, so plain strings suffice. When empty (no right or no known clients) the
  // column falls back to free text.
  readonly sourceIpOptions = computed<string[]>(() => {
    const dict = this.clientsService.clientsResource.value()?.result?.value ?? {};
    const ips = new Set<string>();
    for (const entries of Object.values(dict)) {
      for (const entry of entries) {
        if (entry.ip) {
          ips.add(entry.ip);
        }
      }
    }
    return Array.from(ips).sort((a, b) => a.localeCompare(b));
  });
  readonly showSourceIpMenu = computed(() => this.sourceIpOptions().length > 0);

  // Is any time filter active (a bound set, or a range narrowed on the slider)? Gates whether the picker shows a range.
  private readonly hasTimeFilter = computed(
    () => !!(this.authenticationLogService.timestampFrom() || this.authenticationLogService.timestampTo())
  );
  // The date-range picker's start/end mirror the slider *window* (its min/max), not the narrowed filter, so dragging
  // the slider leaves the picked range in place — the picker only ever defines the outer bounds. Empty when no time
  // filter is active; the end stays open while the window runs up to "now".
  readonly rangePickerStart = computed<Date | null>(() => (this.hasTimeFilter() ? new Date(this.windowStartMs()) : null));
  readonly rangePickerEnd = computed<Date | null>(() =>
    this.hasTimeFilter() && !this.openEndedWindow() ? new Date(this.windowEndMs()) : null
  );
  // Label on the date-range button: the neutral default with no range set, a friendly "Last X" period when the active
  // range ends at ~now and matches a preset span, otherwise "Custom range".
  readonly dateRangeLabel = computed(() => {
    const fromIso = this.authenticationLogService.timestampFrom();
    const toIso = this.authenticationLogService.timestampTo();
    if (!fromIso && !toIso) {
      return $localize`Date range`;
    }
    if (fromIso) {
      const now = Date.now();
      const endMs = toIso ? new Date(toIso).getTime() : now;
      // Only a range ending at ~now reads as a "Last X" period; a historical range stays "Custom range".
      if (now - endMs < MS_PER_DAY) {
        const duration = endMs - new Date(fromIso).getTime();
        const preset = PRESET_LABELS.find((entry) => Math.abs(duration - entry.ms) <= Math.max(entry.ms * 0.05, MS_PER_DAY));
        if (preset) {
          return preset.label;
        }
      }
    }
    return $localize`Custom range`;
  });

  readonly rangeSliderSteps = RANGE_SLIDER_STEPS;
  // A "now" reference for open-ended windows (those running up to the present). Re-sampled when a new window starts so
  // the math below reads a stable now.
  private readonly nowAnchorMs = signal(Date.now());
  // Default window start: the oldest recorded entry (kept at least a day back), or the widest fallback until it loads.
  readonly defaultWindowStartMs = computed(() => {
    const oldest = this.authenticationLogService.oldestTimestamp();
    const end = this.nowAnchorMs();
    return oldest ? Math.min(end - MS_PER_DAY, new Date(oldest).getTime()) : end - DEFAULT_SLIDER_WINDOW_MS;
  });
  // The slider window [start, end] — its zoom. Defaults to oldest→now; a date-range selection zooms it to the picked
  // span so e.g. a single day fills the whole track. Writable so dragging the thumbs does not re-zoom it.
  readonly windowStartMs = linkedSignal(() => this.defaultWindowStartMs());
  readonly windowEndMs = linkedSignal(() => this.nowAnchorMs());
  // Whether the window runs up to "now" (an open upper bound): true for the default / start-only window, false once an
  // end date bounds it. Governs whether the end thumb at its max means "now"/open (no end_time) or that concrete end.
  private readonly openEndedWindow = signal(true);
  // Thumb positions (0 = window start .. RANGE_SLIDER_STEPS = window end), derived from the active time filter
  // (relative to the window). Writable during a drag; each recomputes on the next timestamp/window change.
  readonly rangeStart = linkedSignal(() => this.isoToSliderPos(this.authenticationLogService.timestampFrom(), 0));
  readonly rangeEnd = linkedSignal(() =>
    this.isoToSliderPos(this.authenticationLogService.timestampTo(), RANGE_SLIDER_STEPS)
  );
  // The range summary shows the window's extent (its min/max), not the dragged thumbs, so it stays a stable reference
  // for the axis. The time-of-day is dropped once the window spans more than a day; an open window reads "now" at its
  // max.
  private summaryFormat(ms: number): string {
    const format = this.windowEndMs() - this.windowStartMs() > MS_PER_DAY ? "yyyy-MM-dd" : "yyyy-MM-dd HH:mm";
    return formatDate(ms, format, "en-US");
  }

  readonly rangeSummaryFrom = computed(() => this.summaryFormat(this.windowStartMs()));
  readonly rangeSummaryTo = computed(() =>
    this.openEndedWindow() ? $localize`now` : this.summaryFormat(this.windowEndMs())
  );

  // Activity histogram drawn behind the slider: the loaded entries' timestamps bucketed across the slider window,
  // each bar normalized (0..1) to the busiest bucket. Reflects the current page only, so it is an indication of
  // activity, not the full total.
  readonly activityBinCount = 48;
  readonly activityHistogram = computed<number[]>(() => {
    const bins = new Array<number>(this.activityBinCount).fill(0);
    const start = this.windowStartMs();
    const span = this.windowEndMs() - start;
    for (const entry of this.dataSource().data) {
      const t = entry.timestamp ? new Date(entry.timestamp).getTime() : NaN;
      const fraction = (t - start) / span;
      if (fraction < 0 || fraction > 1) {
        continue;
      }
      bins[Math.min(this.activityBinCount - 1, Math.floor(fraction * this.activityBinCount))]++;
    }
    const max = Math.max(1, ...bins);
    return bins.map((count) => count / max);
  });

  constructor() {
    // Load known clients for the source-IP options (no-op without the `clienttype` right; the resource gates on it).
    this.clientsService.requestClientsForAutocomplete();
    // Keep the time filter in sync with edits made directly to the start_time/end_time entries in the main filter
    // text (the slider/date picker write the same signals via applyTimeRange).
    effect(() => this.syncTimeFilterFromText());
  }

  // Drive the time filter from the start_time/end_time entries in the filter text. Guards keep re-mirroring the signal
  // into the chip from looping and leave an unparsable, in-progress edit untouched instead of clearing an active
  // filter; removing or emptying an entry clears its bound.
  private syncTimeFilterFromText(): void {
    const map = this.authenticationLogService.authenticationLogFilter().filterMap;
    this.syncBoundFromText(map, "start_time", this.authenticationLogService.timestampFrom);
    this.syncBoundFromText(map, "end_time", this.authenticationLogService.timestampTo);
  }

  private syncBoundFromText(map: Map<string, string>, key: string, bound: WritableSignal<string | null>): void {
    const current = bound();
    const chip = map.get(key);
    // Chip still equals what we mirrored out of the signal -> the user did not edit it; nothing to do.
    if ((chip ?? "") === (current ? toFilterDisplay(current) : "")) {
      return;
    }
    if (!chip || !chip.trim()) {
      if (current !== null) {
        bound.set(null);
      }
      return;
    }
    const parsed = parseFilterTimestamp(chip);
    if (parsed && parsed !== current) {
      bound.set(parsed);
    }
  }

  @ViewChild("filterHTMLInputElement", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;

  totalLength: WritableSignal<number> = linkedSignal({
    source: () =>
      this.authenticationLogService.authenticationLogResource.hasValue()
        ? this.authenticationLogService.authenticationLogResource.value()
        : undefined,
    computation: (resource, previous) => resource?.result?.value?.count ?? previous?.value ?? 0
  });
  emptyResource: WritableSignal<AuthenticationLogEntry[]> = linkedSignal({
    source: this.authenticationLogService.pageSize,
    computation: (pageSize: number) =>
      Array.from(
        { length: pageSize },
        () => Object.fromEntries(this.columnKeysMap.map((col) => [col.key, ""])) as unknown as AuthenticationLogEntry
      )
  });
  dataSource: WritableSignal<MatTableDataSource<AuthenticationLogEntry>> = linkedSignal({
    source: () =>
      this.authenticationLogService.authenticationLogResource.hasValue()
        ? this.authenticationLogService.authenticationLogResource.value()
        : undefined,
    computation: (resource, previous) => {
      if (resource) {
        return new MatTableDataSource(resource.result?.value?.auth_logs);
      }
      return previous?.value ?? new MatTableDataSource(this.emptyResource());
    }
  });
  pageSizeOptions = computed(() =>
    [...new Set([...this.tableUtilsService.pageSizeOptions(), this.authenticationLogService.pageSize()])].sort(
      (a, b) => a - b
    )
  );
  noDataText = computed(() =>
    Object.keys(this.authenticationLogService.filterParams()).length > 0 ||
    this.authenticationLogService.timestampFrom() ||
    this.authenticationLogService.timestampTo()
      ? $localize`No authentication log entries matching the filter.`
      : $localize`No authentication log entries.`
  );

  onPageEvent(event: PageEvent): void {
    this.authenticationLogService.pageSize.set(event.pageSize);
    // mat-paginator emits a 0-based index; the service/API page is 1-based.
    this.authenticationLogService.pageIndex.set(event.pageIndex + 1);
  }

  onKeywordClick(filterKeyword: string): void {
    this.authenticationLogService.authenticationLogFilter.set(
      this.tableUtilsService.toggleKeywordInFilter({
        keyword: filterKeyword,
        currentValue: this.authenticationLogService.authenticationLogFilter()
      })
    );
    this.filterInput?.nativeElement.focus();
  }

  getFilterIconName(keyword: string): string {
    return this.authenticationLogService.authenticationLogFilter().hasKey(keyword) ? "filter_alt_off" : "filter_alt";
  }

  // Three-state sort cycle; clearing falls back to timestamp desc with a neutral direction so no column shows active.
  onSortClick(columnKey: string): void {
    this.tableUtilsService.onSortButtonClick(columnKey, this.sort, { active: "timestamp", direction: "" });
  }

  // Clears both the text and the time filter, bound to the input's clear (X) button. The time filter lives in its own
  // signals, so it must be cleared alongside the text.
  clearAllFilters(): void {
    this.clearTimeFilter();
    this.authenticationLogService.clearFilter();
  }

  clearTimeFilter(): void {
    // Re-anchor "now" so the default window is recomputed from the current moment (see defaultWindowStartMs).
    this.nowAnchorMs.set(Date.now());
    this.openEndedWindow.set(true);
    this.windowStartMs.set(this.defaultWindowStartMs());
    this.windowEndMs.set(this.nowAnchorMs());
    this.applyTimeRange(null, null);
  }

  // Date-range picker edits: a chosen date sets the whole local day as the bound (inclusive), while the other bound is
  // preserved; clearing a field (null) drops that bound. The picked range also zooms the slider window so the selected
  // span fills the track (e.g. a single day -> 24 hours).
  onRangeStartDateChange(date: Date | null): void {
    const fromIso = date ? startOfDayIso(date) : null;
    const toIso = this.authenticationLogService.timestampTo();
    this.zoomSliderToRange(fromIso, toIso);
    this.applyTimeRange(fromIso, toIso);
  }

  onRangeEndDateChange(date: Date | null): void {
    const fromIso = this.authenticationLogService.timestampFrom();
    const toIso = date ? endOfDayIso(date) : null;
    this.zoomSliderToRange(fromIso, toIso);
    this.applyTimeRange(fromIso, toIso);
  }

  // Zoom the slider window to the picked range so the selected span fills the whole track. A missing bound widens the
  // window to that edge: no start -> back to the default oldest edge; no end -> an open window running up to now.
  private zoomSliderToRange(fromIso: string | null, toIso: string | null): void {
    this.nowAnchorMs.set(Date.now());
    this.openEndedWindow.set(!toIso);
    this.windowStartMs.set(fromIso ? new Date(fromIso).getTime() : this.defaultWindowStartMs());
    this.windowEndMs.set(toIso ? new Date(toIso).getTime() : this.nowAnchorMs());
  }

  // Update the thumb position live while dragging (labels only, no reload); commitTimeRange applies it on release.
  onRangeStartInput(pos: number): void {
    this.rangeStart.set(pos);
  }

  onRangeEndInput(pos: number): void {
    this.rangeEnd.set(pos);
  }

  // Apply the slider's current [start, end] thumbs as the time filter, on thumb release / keyboard commit.
  commitTimeRange(): void {
    this.applyTimeRange(this.sliderPosToIso(this.rangeStart(), false), this.sliderPosToIso(this.rangeEnd(), true));
  }

  // Thumb value indicator. The format tracks the window's zoom so the label is useful at every span: time-of-day for
  // short windows, day for medium, month for the widest. The precise from/to is always shown in the summary line.
  readonly formatSliderThumb = (pos: number): string => {
    const iso = this.sliderPosToIso(pos, false)!;
    const windowMs = this.windowEndMs() - this.windowStartMs();
    if (windowMs <= 3 * MS_PER_DAY) {
      return formatDate(iso, "HH:mm", "en-US");
    }
    if (windowMs <= 100 * MS_PER_DAY) {
      return formatDate(iso, "MMM d", "en-US");
    }
    return formatDate(iso, "MMM", "en-US");
  };

  // Single writer of the time filter: set timestampFrom/To (the source of truth for the API params) and mirror them
  // into the filter text as start_time/end_time chips. A null bound removes its chip and its API param.
  private applyTimeRange(fromIso: string | null, toIso: string | null): void {
    this.authenticationLogService.timestampFrom.set(fromIso);
    this.authenticationLogService.timestampTo.set(toIso);
    let filter = this.authenticationLogService.authenticationLogFilter();
    filter = fromIso ? filter.addEntry("start_time", toFilterDisplay(fromIso)) : filter.removeKey("start_time");
    filter = toIso ? filter.addEntry("end_time", toFilterDisplay(toIso)) : filter.removeKey("end_time");
    this.authenticationLogService.authenticationLogFilter.set(filter);
  }

  // Map a slider position (0 = window start, max = window end) to an ISO timestamp, spread linearly over the window.
  // For an open-ended window the end thumb at its maximum means "up to now" -> null (no upper bound, no end_time).
  private sliderPosToIso(pos: number, isEnd: boolean): string | null {
    if (isEnd && pos >= RANGE_SLIDER_STEPS && this.openEndedWindow()) {
      return null;
    }
    const start = this.windowStartMs();
    const span = this.windowEndMs() - start;
    const ms = start + (pos / RANGE_SLIDER_STEPS) * span;
    // Emit whole-second precision to match the seconds shown in the chip/summary: a sub-second value looks identical
    // to the display yet silently mismatches an entry (which carries sub-second precision). Floor the inclusive start
    // so a boundary entry stays >= it (includes the oldest); ceil the inclusive end so it stays <= it.
    const seconds = isEnd ? Math.ceil(ms / 1000) : Math.floor(ms / 1000);
    return new Date(seconds * 1000).toISOString();
  }

  // Inverse of sliderPosToIso: place an ISO timestamp on the slider axis (relative to the current window), clamped to
  // the visible range. A null bound falls back to the given edge (start -> window start, end -> window end).
  private isoToSliderPos(iso: string | null, fallback: number): number {
    if (!iso) {
      return fallback;
    }
    const start = this.windowStartMs();
    const span = this.windowEndMs() - start;
    const fraction = (new Date(iso).getTime() - start) / span;
    return Math.min(RANGE_SLIDER_STEPS, Math.max(0, Math.round(fraction * RANGE_SLIDER_STEPS)));
  }

  // Predefined-value filters (event_type, realm) hold one or more comma-separated values the API splits as CSV.
  // The shared multi-select-filter component renders these and emits the full next selection.
  selectedFilterValues(keyword: string): string[] {
    return this.splitCsv(this.authenticationLogService.authenticationLogFilter().getValueOfKey(keyword));
  }

  setFilterValues(keyword: string, values: string[]): void {
    const currentFilter = this.authenticationLogService.authenticationLogFilter();
    const newFilter = values.length
      ? currentFilter.addEntry(keyword, values.join(","))
      : currentFilter.removeKey(keyword);
    this.authenticationLogService.authenticationLogFilter.set(newFilter);
  }

  // Whether a @default cell shows the inline "filter by this value" button. Columns whose header already offers a
  // value picker don't need it, which is dynamic for the client_label.
  showInlineCellFilter(columnKey: string): boolean {
    if (columnKey === "client_label") return false;
    if (columnKey === "source_ip") return !this.showSourceIpMenu();
    return true;
  }

  // Localized tooltip for a cell's inline filter button, falling back to the generic phrasing.
  filterTooltip(columnKey: string): string {
    return FILTER_TOOLTIPS[columnKey] ?? $localize`Filter by this value`;
  }

  // Inline "filter by this value" action on a cell: add the value to the column's filter (a no-op if already there).
  addFilterValue(keyword: string, value: string): void {
    const current = this.selectedFilterValues(keyword);
    if (!current.includes(value)) {
      this.setFilterValues(keyword, [...current, value]);
    }
  }

  // "Enter custom value" from a selection menu: ensure the key is present in the main filter input and focus it, so
  // the user can type a free value (no wildcard) just like the plain free-text filter columns. The focus is deferred
  // because the menu item click closes the menu, which restores focus to its trigger afterwards — a synchronous
  // focus() would be overridden.
  onAddCustomFilter(keyword: string): void {
    this.authenticationLogService.authenticationLogFilter.set(
      this.authenticationLogService.authenticationLogFilter().addKey(keyword)
    );
    setTimeout(() => this.filterInput?.nativeElement.focus());
  }

  // Color a row by its event's outcome (success/failure/pending); unknown/empty/not-yet-loaded values stay unstyled.
  getEventTypeClass(value: string): string {
    const outcome = this.outcomeByEventType().get(value);
    return outcome ? (OUTCOME_CLASS[outcome] ?? "") : "";
  }

  formatInfo(value: AuthenticationLogEntry["other_info"]): string {
    return value ? JSON.stringify(value) : "";
  }

  // Render other_info as "key: value" rows. Scalars show as-is and arrays as a comma-separated list. A nested object
  // (e.g. the `truncated` overflow key) becomes a one-level sub-list; anything deeper is compact JSON.
  infoEntries(value: AuthenticationLogEntry["other_info"]): InfoEntry[] {
    if (!value) return [];
    return Object.entries(value).map(([key, raw]) =>
      this.isPlainObject(raw)
        ? { key, children: Object.entries(raw).map(([k, v]) => ({ key: k, value: this.formatInfoValue(v) })) }
        : { key, value: this.formatInfoValue(raw) }
    );
  }

  private formatInfoValue(value: unknown): string {
    if (value === null || value === undefined) return "";
    if (Array.isArray(value)) return value.map((entry) => this.formatInfoValue(entry)).join(", ");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  private isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }

  // Badge for an admin principal, or null for a regular user / unknown value so the template renders nothing.
  userRoleBadge(value: string | null | undefined): { label: string; tooltip: string; class: string } | null {
    return (value && USER_ROLE_BADGES[value]) || null;
  }

  // The serial column may hold several comma-separated serials; render each as its own token link.
  splitSerials(value: string | null | undefined): string[] {
    return this.splitCsv(value);
  }

  private splitCsv(value: string | null | undefined): string[] {
    return value
      ? value
          .split(",")
          .map((entry) => entry.trim())
          .filter((entry) => entry.length > 0)
      : [];
  }
}
