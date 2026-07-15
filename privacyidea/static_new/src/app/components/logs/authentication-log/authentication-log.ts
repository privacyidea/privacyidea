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
  ElementRef,
  inject,
  linkedSignal,
  signal,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatDividerModule } from "@angular/material/divider";
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
  { key: "timestamp", label: $localize`Timestamp`, filterable: true, sortable: true },
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

const TIME_PRESETS: readonly { key: string; label: string }[] = [
  { key: "1h", label: $localize`Last 1 hour` },
  { key: "24h", label: $localize`Last 24 hours` },
  { key: "7d", label: $localize`Last 7 days` },
  { key: "30d", label: $localize`Last 30 days` },
  { key: "3m", label: $localize`Last 3 months` },
  { key: "6m", label: $localize`Last 6 months` },
  { key: "1y", label: $localize`Last year` }
];

// Computes the start of a time period relative to now, used by selectTimePreset to set the `from` filter.
// period: a key from TIME_PRESETS, e.g. "1h", "24h", "7d", "30d", "3m", "1y" (number + unit h/d/m/y).
// Returns an ISO 8601 string, e.g. "2026-06-02T10:00:00.000Z".
function computePeriodStart(period: string): string {
  const match = /^(\d+)([hdmy])$/.exec(period);
  if (!match) throw new Error(`Unknown period key: ${period}`);
  const amount = parseInt(match[1], 10);
  const unit = match[2];
  const now = new Date();
  switch (unit) {
    case "h":
      return new Date(now.getTime() - amount * 3_600_000).toISOString();
    case "d":
      return new Date(now.getTime() - amount * 86_400_000).toISOString();
    case "m": {
      const date = new Date(now);
      date.setMonth(date.getMonth() - amount);
      return date.toISOString();
    }
    case "y": {
      const date = new Date(now);
      date.setFullYear(date.getFullYear() - amount);
      return date.toISOString();
    }
    default:
      throw new Error(`Unknown time unit: ${unit}`);
  }
}

// The custom-range slider has a fixed number of positions (its resolution); the time span they cover is dynamic
// (sliderWindowMs) and follows the selected preset. It defaults to the widest preset (1 year).
const RANGE_SLIDER_STEPS = 200;
const MS_PER_DAY = 86_400_000;
const DEFAULT_SLIDER_WINDOW_MS = 365 * MS_PER_DAY;

// Converts an ISO 8601 string to the human-readable format shown in the active-filter chip.
// Input: ISO 8601, e.g. "2026-06-02T10:00:00.000Z". Output: "2026-06-02 10:00:00 +00:00".
function toFilterDisplay(isoString: string): string {
  return formatDate(isoString, "yyyy-MM-dd HH:mm:ss ZZZZZ", "en-US");
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
    MatDividerModule,
    MatIconModule,
    MatMenuModule,
    MatSliderModule,
    MatTooltipModule
  ],
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

  readonly timePresets = TIME_PRESETS;
  // Highlighted preset button. Component-local: it reflects the last preset the user clicked, not the underlying
  // timestamp filter, so it is cleared whenever a custom range or a clear is applied.
  readonly selectedPreset = signal<string | null>(null);

  readonly rangeSliderSteps = RANGE_SLIDER_STEPS;
  // The time span the slider covers (its zoom level): a preset's duration, or the default window after a clear.
  readonly sliderWindowMs = signal(DEFAULT_SLIDER_WINDOW_MS);
  // Thumb positions (0 = start of the window .. RANGE_SLIDER_STEPS = now), derived from the active time filter
  // (relative to sliderWindowMs). Writable during a drag; each recomputes on the next timestamp/window change.
  readonly rangeStart = linkedSignal(() => this.isoToSliderPos(this.authenticationLogService.timestampFrom(), 0));
  readonly rangeEnd = linkedSignal(() =>
    this.isoToSliderPos(this.authenticationLogService.timestampTo(), RANGE_SLIDER_STEPS)
  );
  // Human-readable from/to for the range summary line; the end thumb at its maximum reads as "now".
  readonly rangeSummaryFrom = computed(() =>
    formatDate(this.sliderPosToIso(this.rangeStart(), false)!, "yyyy-MM-dd HH:mm", "en-US")
  );
  readonly rangeSummaryTo = computed(() => {
    const iso = this.sliderPosToIso(this.rangeEnd(), true);
    return iso ? formatDate(iso, "yyyy-MM-dd HH:mm", "en-US") : $localize`now`;
  });

  // Activity histogram drawn behind the slider: the loaded entries' timestamps bucketed across the slider window,
  // each bar normalized (0..1) to the busiest bucket. Reflects the current page only, so it is an indication of
  // activity, not the full total.
  readonly activityBinCount = 48;
  readonly activityHistogram = computed<number[]>(() => {
    const bins = new Array<number>(this.activityBinCount).fill(0);
    const windowMs = this.sliderWindowMs();
    const start = Date.now() - windowMs;
    for (const entry of this.dataSource().data) {
      const t = entry.timestamp ? new Date(entry.timestamp).getTime() : NaN;
      const fraction = (t - start) / windowMs;
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

  selectTimePreset(key: string): void {
    this.selectedPreset.set(key);
    const startIso = computePeriodStart(key);
    // Zoom the slider window to this preset's span; the thumbs then sit at its edges (start = oldest, end = now).
    this.sliderWindowMs.set(Date.now() - new Date(startIso).getTime());
    this.applyTimeRange(startIso, null);
  }

  clearTimeFilter(): void {
    this.selectedPreset.set(null);
    this.sliderWindowMs.set(DEFAULT_SLIDER_WINDOW_MS);
    this.applyTimeRange(null, null);
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
    this.selectedPreset.set(null);
    this.applyTimeRange(this.sliderPosToIso(this.rangeStart(), false), this.sliderPosToIso(this.rangeEnd(), true));
  }

  // Thumb value indicator. The format tracks the window's zoom so the label is useful at every span: time-of-day for
  // short windows, day for medium, month for the widest. The precise from/to is always shown in the summary line.
  readonly formatSliderThumb = (pos: number): string => {
    const iso = this.sliderPosToIso(pos, false)!;
    const windowMs = this.sliderWindowMs();
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

  // Map a slider position (0 = start of the window, max = now) to an ISO timestamp, spread linearly over the current
  // sliderWindowMs. The end thumb at its maximum means "up to now" -> null (no upper bound, so no end_time param).
  private sliderPosToIso(pos: number, isEnd: boolean): string | null {
    if (isEnd && pos >= RANGE_SLIDER_STEPS) {
      return null;
    }
    const windowMs = this.sliderWindowMs();
    return new Date(Date.now() - windowMs + (pos / RANGE_SLIDER_STEPS) * windowMs).toISOString();
  }

  // Inverse of sliderPosToIso: place an ISO timestamp on the slider axis (relative to the current window), clamped to
  // the visible range. A null bound falls back to the given edge (start -> oldest, end -> now).
  private isoToSliderPos(iso: string | null, fallback: number): number {
    if (!iso) {
      return fallback;
    }
    const windowMs = this.sliderWindowMs();
    const fraction = 1 - (Date.now() - new Date(iso).getTime()) / windowMs;
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
