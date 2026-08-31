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
import { MatDivider } from "@angular/material/divider";
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
import { ConditionalAccessCell } from "./cells/conditional-access-cell/conditional-access-cell";
import { InfoCell } from "./cells/info-cell/info-cell";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { TruncationTooltipDirective } from "@components/shared/directives/truncation-tooltip.directive";
import { MultiSelectFilterComponent } from "@components/shared/multi-select-filter/multi-select-filter.component";
import { MultiSelectFilterOption } from "@components/shared/multi-select-filter/multi-select-filter-option";
import { MultiSelectMenuComponent } from "@components/shared/multi-select-filter/multi-select-menu/multi-select-menu.component";
import { USER_AGENT_PRESETS } from "@constants/user-agent.constants";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ClientsService, ClientsServiceInterface } from "@services/clients/clients.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface
} from "@services/conditional-access/conditional-access-policy.service";
import {
  AuthenticationLogEntry,
  AuthenticationLogService,
  AuthenticationLogServiceInterface
} from "@services/authentication-log/authentication-log.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";

// CSS highlight class per event outcome; outcome values come from the backend's AuthEventOutcome (GET
// /authenticationlog/eventtypes), and this file only maps each one to a color.
const OUTCOME_CLASS: Record<string, string> = {
  success: "highlight-true",
  failure: "highlight-false",
  pending: "highlight-warning"
};

// User-identifying columns hidden in self-service: every row is already the logged-in user, and their realm/user
// links target admin-only pages.
const USER_SCOPED_COLUMN_KEYS = ["username", "realm"];

// Single source for user roles: filter-menu label plus badge metadata for admin roles; regular users get no badge
// since they are the default, appearing on almost every row.
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

// `sortable` mirrors SORTABLE_COLUMNS in privacyidea/lib/conditional_access/authentication_log.py; every column is
// sortable except `other_info`, a JSON column the backend cannot order on meaningfully.
const columnKeysMap: { key: string; label: string; filterable: boolean; sortable: boolean }[] = [
  // The timestamp filter lives in the table-action row (preset menu + custom-range slider), not the column header, so
  // the header only offers sorting.
  { key: "timestamp", label: $localize`Timestamp`, filterable: false, sortable: true },
  // Directly after the timestamp: the attempt id groups the rows of one logical attempt, so it reads as part of
  // locating a row rather than a detail of it.
  { key: "attempt_id", label: $localize`Attempt ID`, filterable: true, sortable: true },
  { key: "event_type", label: $localize`Event Type`, filterable: true, sortable: true },
  { key: "username", label: $localize`User`, filterable: true, sortable: true },
  { key: "realm", label: $localize`Realm`, filterable: true, sortable: true },
  { key: "source_ip", label: $localize`Source IP`, filterable: true, sortable: true },
  { key: "client_label", label: $localize`Client`, filterable: true, sortable: true },
  { key: "serial", label: $localize`Serial`, filterable: true, sortable: true },
  { key: "transaction_id", label: $localize`Transaction ID`, filterable: true, sortable: true },
  // Neither is sortable: other_info is JSON, and conditional-access outcomes live in their own table, read alongside
  // each entry (its filter menu is documented at OUTCOME_FILTER_KEYS below).
  {
    key: "conditional_access_outcomes",
    label: $localize`Conditional Access Outcome`,
    filterable: true,
    sortable: false
  },
  { key: "other_info", label: $localize`Info`, filterable: false, sortable: false }
];

// The columns that render a list rather than a scalar, each via its own cell component (see ./cells): they share their
// width/scroll behavior (decided here, since it depends on the whole page) and their look (cells/_info-list.scss), not
// their rendering logic.
const INFO_COLUMN_KEYS = ["conditional_access_outcomes", "other_info"];

// The Conditional access column filters on three keys at once, hence a header menu instead of the single-key toggle
// other columns use; the keys mirror the backend's _FILTER_PARAMS (api/authentication_log.py) and are also typeable in
// the main filter input as advanced filters.
const OUTCOME_FILTER_KEYS = ["ca_action_type", "ca_policy_name", "ca_dry_run"];

// The two values of the dry-run filter; "Both" is the absence of the key, reached the same way every other filter is
// cleared, rather than by a third pseudo-value.
const DRY_RUN_OPTIONS: readonly MultiSelectFilterOption[] = [
  { label: $localize`Enforced only`, value: "false" },
  { label: $localize`Dry run only`, value: "true" }
];

// Local start/end-of-day ISO bounds for a date chosen in the range picker: the picker yields a native Date at local
// midnight, and since the log renders timestamps in local time, the bounds are the local day's edges (inclusive end at
// 23:59:59) converted to the ISO string the API filter expects.
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

// The custom-range slider has a fixed number of positions (its resolution) mapped onto a dynamic time span (the
// window), which defaults to the span from the oldest entry to now, or the widest fallback until that loads.
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

// Inverse of toFilterDisplay for the editable start_time/end_time chips: parses the mirrored display, plain ISO, or a
// partial typed datetime into an ISO string, returning null for an empty or unparsable value.
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

// Full, independently-translatable tooltip per column with an inline filter button, kept as complete sentences (not
// noun-interpolated) so each language can phrase its grammar correctly; a column with no entry falls back to the
// button's generic default.
const FILTER_TOOLTIPS: Record<string, string> = {
  username: $localize`Filter by this user`,
  source_ip: $localize`Filter by this source IP`,
  serial: $localize`Filter by this serial`,
  transaction_id: $localize`Filter by this transaction ID`,
  attempt_id: $localize`Filter by this attempt ID`
};

// Columns whose value is clipped instead of widening the table: the full value stays reachable via the truncation
// tooltip, the copy button and the inline filter. Width classes (see .cell-truncate-* rules) differ per column - ids
// read by their leading characters, a client label read as a name - but never narrow a column past its header's own
// width (label + filter + sort icons).
const TRUNCATED_COLUMN_CLASSES: Record<string, string> = {
  attempt_id: "cell-truncate-id",
  transaction_id: "cell-truncate-id",
  client_label: "cell-truncate-client"
};

// Key fragments that read as acronyms rather than words when an other_info key is humanized for display.
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
    TruncationTooltipDirective,
    DatePipe,
    ClearableInputComponent,
    ConditionalAccessCell,
    InfoCell,
    MultiSelectFilterComponent,
    MultiSelectMenuComponent,
    MatDivider,
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
  readonly scrollableColumnKeys = ["serial", ...INFO_COLUMN_KEYS];
  // Client filter: shows the friendly user-agent name but filters by its identifier prefix, since client_label stores
  // the full user-agent string including the version; the multi-select component appends the trailing "*". REVIEW: once
  // selected, the shared filter input displays the raw stored value (e.g. `client_label: privacyIDEA-Keycloak*`) not
  // the friendly name the user picked; consider mapping it back for display.
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
  protected readonly conditionalAccessPolicyService: ConditionalAccessPolicyServiceInterface =
    inject(ConditionalAccessPolicyService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  sort = this.authenticationLogService.sort;

  readonly eventTypeOptions = computed<string[]>(() =>
    this.authenticationLogService.eventTypes().map((entry) => entry.name)
  );
  private readonly outcomeByEventType = computed<Map<string, string>>(
    () => new Map(this.authenticationLogService.eventTypes().map((entry) => [entry.name, entry.outcome]))
  );

  // Columns to render: a self-service user only ever sees their own entries, so the user-identifying columns are
  // hidden, since their realm/user links target admin-only pages anyway.
  readonly visibleColumns = computed(() =>
    this.authService.isSelfServiceUser()
      ? this.columnKeysMap.filter((column) => !USER_SCOPED_COLUMN_KEYS.includes(column.key))
      : this.columnKeysMap
  );
  readonly visibleColumnKeys = computed(() => this.visibleColumns().map((column) => column.key));

  // Source-IP filter options come from the known clients, which requires the `clienttype` right and so may be empty;
  // IPs match exactly and display equals value, so plain strings suffice, and an empty list falls back to free text.
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
  // The date-range picker's start/end mirror the slider window's min/max, not the narrowed filter, so dragging the
  // slider never moves the picked range; it is empty with no time filter active, with an open end while the window runs
  // up to "now".
  readonly rangePickerStart = computed<Date | null>(() =>
    this.hasTimeFilter() ? new Date(this.windowStartMs()) : null
  );
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
        const preset = PRESET_LABELS.find(
          (entry) => Math.abs(duration - entry.ms) <= Math.max(entry.ms * 0.05, MS_PER_DAY)
        );
        if (preset) {
          return preset.label;
        }
      }
    }
    return $localize`Custom range`;
  });

  readonly rangeSliderSteps = RANGE_SLIDER_STEPS;
  // A "now" reference for open-ended windows (those running up to the present), re-sampled when a new window starts
  // so the math below reads a stable value.
  private readonly nowAnchorMs = signal(Date.now());
  // Default window start: the oldest recorded entry (kept at least a day back), or the widest fallback until it loads.
  readonly defaultWindowStartMs = computed(() => {
    const oldest = this.authenticationLogService.oldestTimestamp();
    const end = this.nowAnchorMs();
    return oldest ? Math.min(end - MS_PER_DAY, new Date(oldest).getTime()) : end - DEFAULT_SLIDER_WINDOW_MS;
  });
  // The slider window [start, end] is its zoom, defaulting to oldest→now; a date-range selection zooms it to the picked
  // span (e.g. a single day fills the whole track), and it stays writable so dragging the thumbs never re-zooms it.
  readonly windowStartMs = linkedSignal(() => this.defaultWindowStartMs());
  readonly windowEndMs = linkedSignal(() => this.nowAnchorMs());
  // Whether the window runs up to "now" (an open upper bound): true for the default or start-only window, false once
  // an end date bounds it; this governs whether the end thumb at its max means open/"now" or a concrete end.
  private readonly openEndedWindow = signal(true);
  // Thumb positions (0 = window start .. RANGE_SLIDER_STEPS = window end) derive from the active time filter relative
  // to the window, staying writable during a drag and recomputing on the next timestamp or window change.
  readonly rangeStart = linkedSignal(() => this.isoToSliderPos(this.authenticationLogService.timestampFrom(), 0));
  readonly rangeEnd = linkedSignal(() =>
    this.isoToSliderPos(this.authenticationLogService.timestampTo(), RANGE_SLIDER_STEPS)
  );
  // The range summary shows the window's extent (its min/max), not the dragged thumbs, so it stays a stable reference
  // for the axis; it drops the time-of-day once the window spans more than a day, and an open window reads "now" at its
  // max.
  private summaryFormat(ms: number): string {
    const format = this.windowEndMs() - this.windowStartMs() > MS_PER_DAY ? "yyyy-MM-dd" : "yyyy-MM-dd HH:mm";
    return formatDate(ms, format, "en-US");
  }

  readonly rangeSummaryFrom = computed(() => this.summaryFormat(this.windowStartMs()));
  readonly rangeSummaryTo = computed(() =>
    this.openEndedWindow() ? $localize`now` : this.summaryFormat(this.windowEndMs())
  );

  // Activity histogram drawn behind the slider: the loaded entries' timestamps are bucketed across the slider window,
  // with each bar normalized (0..1) to the busiest bucket; it reflects the current page only, an indication of
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
    // "All" is the default page size: the first response tells us how many entries there are, and the page size widens
    // to that exactly once, so a size the user picks afterwards stands.
    effect(() => this.applyDefaultPageSize());
  }

  private defaultPageSizeApplied = false;

  private applyDefaultPageSize(): void {
    const total = this.totalLength();
    if (this.defaultPageSizeApplied || total <= 0) {
      return;
    }
    this.defaultPageSizeApplied = true;
    if (total > this.authenticationLogService.pageSize()) {
      this.authenticationLogService.pageSize.set(total);
    }
  }

  // Drives the time filter from the start_time/end_time entries in the filter text; guards keep the signal-to-chip
  // mirroring from looping, leave an unparsable in-progress edit untouched without clearing an active filter, and clear
  // a bound only when its entry is removed or emptied.
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
  // An info-like column only earns its width when something is actually in it: it is widened for the current page when
  // at least one entry has content for it, and otherwise stays as narrow as the table wants.
  readonly hasInfoValues = computed(() =>
    this.dataSource().data.some((entry) => entry.other_info && Object.keys(entry.other_info).length > 0)
  );
  readonly hasOutcomeValues = computed(() =>
    this.dataSource().data.some((entry) => (entry.conditional_access_outcomes?.length ?? 0) > 0)
  );
  // The presets, the active page size, and the total number of matching entries - the last one so the selector also
  // offers "everything on one page", sorted into place among the presets.
  pageSizeOptions = computed(() =>
    [
      ...new Set([
        ...this.tableUtilsService.pageSizeOptions(),
        this.authenticationLogService.pageSize(),
        this.totalLength()
      ])
    ]
      .filter((size) => size > 0)
      .sort((a, b) => a - b)
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

  // The real action vocabulary and the existing policy names both come from the backend, so neither list is duplicated
  // here; they read empty until the resources load, or when the admin lacks `conditional_access_policy_read` (see
  // canReadConditionalAccessPolicies below).
  readonly outcomeActionOptions = computed<string[]>(() => this.conditionalAccessPolicyService.actionTypes());
  readonly outcomePolicyOptions = computed<string[]>(() =>
    [...new Set(this.conditionalAccessPolicyService.policies().map((policy) => policy.name))].sort((a, b) =>
      a.localeCompare(b)
    )
  );
  readonly canReadConditionalAccessPolicies = computed(() =>
    this.authService.actionAllowed("conditional_access_policy_read")
  );
  // How an outcome's policy name becomes a link: it looks up the id of a currently-existing policy with that name from
  // the list this page already loads; without `conditional_access_policy_read` that list is empty, so the cell renders
  // the name as plain text (see policyIdsByName).
  readonly policyIdsByName = computed<ReadonlyMap<string, number>>(
    () => new Map(this.conditionalAccessPolicyService.policies().map((policy) => [policy.name, policy.id]))
  );

  readonly dryRunOptions = DRY_RUN_OPTIONS;
  // The trigger's accessible name states both the rule and the purpose, so it is heard before the menu opens (the
  // menu's own `note` states it too); it is a bound label rather than an i18n-marked attribute, since only a bound
  // label is something the component's tests can read back.
  readonly outcomeFilterLabel = $localize`Filter by conditional access outcome. All conditions must match one and the same outcome.`;
  // "" means the dry-run filter is unset, i.e. both kinds of outcome match.
  readonly dryRunFilter = computed<string>(
    () => this.authenticationLogService.authenticationLogFilter().getValueOfKey("ca_dry_run") ?? ""
  );

  setDryRunFilter(value: string): void {
    this.setFilterValues("ca_dry_run", value ? [value] : []);
  }

  // Drops all three keys at once, so one entry undoes whatever was set in the submenus.
  clearOutcomeFilters(): void {
    let filter = this.authenticationLogService.authenticationLogFilter();
    for (const key of OUTCOME_FILTER_KEYS) {
      filter = filter.removeKey(key);
    }
    this.authenticationLogService.authenticationLogFilter.set(filter);
  }

  // Three-state sort cycle; clearing falls back to timestamp desc with a neutral direction so no column shows active.
  onSortClick(columnKey: string): void {
    this.tableUtilsService.onSortButtonClick(columnKey, this.sort, { active: "timestamp", direction: "" });
  }

  // Clears both the text and the time filter, bound to the input's clear (X) button; the time filter lives in its own
  // signals, so it needs its own explicit clear alongside the text.
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

  // Date-range picker edits: choosing a date sets the whole local day as that bound (inclusive) while preserving the
  // other bound, and clearing a field (null) drops its bound; the picked range also zooms the slider window so the
  // selected span fills the track (e.g. a single day becomes 24 hours).
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

  // Zoom the slider window to the picked range so the selected span fills the whole track; a missing bound widens the
  // window to that edge - no start reverts to the default oldest edge, no end opens the window running up to now.
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

  // Thumb value indicator: the format tracks the window's zoom - time-of-day for short windows, day for medium, month
  // for the widest - while the exact from/to is always shown in the summary line.
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

  // Single writer of the time filter: sets timestampFrom/To (the source of truth for the API params) and mirrors them
  // into the filter text as start_time/end_time chips; a null bound removes both its chip and its API param.
  private applyTimeRange(fromIso: string | null, toIso: string | null): void {
    this.authenticationLogService.timestampFrom.set(fromIso);
    this.authenticationLogService.timestampTo.set(toIso);
    let filter = this.authenticationLogService.authenticationLogFilter();
    filter = fromIso ? filter.addEntry("start_time", toFilterDisplay(fromIso)) : filter.removeKey("start_time");
    filter = toIso ? filter.addEntry("end_time", toFilterDisplay(toIso)) : filter.removeKey("end_time");
    this.authenticationLogService.authenticationLogFilter.set(filter);
  }

  // Maps a slider position (0 = window start, max = window end) to an ISO timestamp, spread linearly over the window;
  // for an open-ended window the end thumb at its maximum means "up to now", so it maps to null (no end_time).
  private sliderPosToIso(pos: number, isEnd: boolean): string | null {
    if (isEnd && pos >= RANGE_SLIDER_STEPS && this.openEndedWindow()) {
      return null;
    }
    const start = this.windowStartMs();
    const span = this.windowEndMs() - start;
    const ms = start + (pos / RANGE_SLIDER_STEPS) * span;
    // Emits whole-second precision to match the seconds shown in the chip/summary, since a sub-second value would look
    // identical there yet silently mismatch an entry's real timestamp; flooring the inclusive start keeps a boundary
    // entry >= it, and ceiling the inclusive end keeps it <= it.
    const seconds = isEnd ? Math.ceil(ms / 1000) : Math.floor(ms / 1000);
    return new Date(seconds * 1000).toISOString();
  }

  // Inverse of sliderPosToIso: places an ISO timestamp on the slider axis relative to the current window, clamped to
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

  // Whether a @default cell shows the inline "filter by this value" button: columns whose header already offers a
  // value picker don't need it. client_label never needs it; source_ip needs it only when its own IP menu is hidden.
  showInlineCellFilter(columnKey: string): boolean {
    if (columnKey === "client_label") return false;
    if (columnKey === "source_ip") return !this.showSourceIpMenu();
    return true;
  }

  // Localized tooltip for a cell's inline filter button, falling back to the generic phrasing.
  filterTooltip(columnKey: string): string {
    return FILTER_TOOLTIPS[columnKey] ?? $localize`Filter by this value`;
  }

  // The width class a clipped column's value carries, or null for a column shown in full.
  truncatedClass(columnKey: string): string | null {
    return TRUNCATED_COLUMN_CLASSES[columnKey] ?? null;
  }

  // Inline "filter by this value" action on a cell: add the value to the column's filter (a no-op if already there).
  addFilterValue(keyword: string, value: string): void {
    const current = this.selectedFilterValues(keyword);
    if (!current.includes(value)) {
      this.setFilterValues(keyword, [...current, value]);
    }
  }

  // "Enter custom value" from a selection menu: ensures the key is present in the main filter input and focuses it, so
  // the user can type a free value (no wildcard) like the plain free-text filter columns. Focus is deferred because the
  // menu closes on click and restores focus to its trigger afterward, which would override a synchronous focus() call.
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

  // Whether *column* renders a list (Info / Conditional access) rather than a scalar, and whether the current page has
  // anything to put in it - together they decide the width treatment.
  isInfoColumn(column: string): boolean {
    return INFO_COLUMN_KEYS.includes(column);
  }

  hasColumnContent(column: string): boolean {
    return column === "conditional_access_outcomes" ? this.hasOutcomeValues() : this.hasInfoValues();
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
