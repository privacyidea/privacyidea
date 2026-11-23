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
import { AuditDateRangeHeaderComponent } from "./audit-date-range-header.component";
import { AuditRangeSelectionStrategy } from "./audit-range-selection-strategy";
import { MatSuffix } from "@angular/material/form-field";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import {
  Component,
  computed,
  effect,
  DestroyRef,
  ElementRef,
  inject,
  Injector,
  linkedSignal,
  signal,
  TemplateRef,
  untracked,
  ViewChild,
  viewChild,
  ViewContainerRef,
  WritableSignal
} from "@angular/core";
import { MatFormField, MatHint, MatLabel } from "@angular/material/form-field";
import { MatPaginator, PageEvent } from "@angular/material/paginator";
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
import { AuditData, AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ROUTE_PATHS } from "@app/route_paths";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { RefocusAfterReloadDirective } from "@components/shared/directives/refocus-after-reload.directive";

import { DatePipe, NgClass } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatCardModule } from "@angular/material/card";
import { provideNativeDateAdapter } from "@angular/material/core";
import {
  DateRange,
  MAT_DATE_RANGE_SELECTION_STRATEGY,
  MatDatepickerModule,
  MatDateRangePicker
} from "@angular/material/datepicker";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatTooltipModule } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { FilterAutocompleteDirective } from "@components/shared/directives/filter-autocomplete.directive";
import { PaginatorCompactRangeDirective } from "@components/shared/directives/paginator-compact-range.directive";
import { PaginatorPageSizeTooltipDirective } from "@components/shared/directives/paginator-page-size-tooltip.directive";
import { ScrollEdgesDirective } from "@components/shared/directives/scroll-edges.directive";
import { TableStateComponent } from "@components/shared/table-state/table-state.component";
import { TableState } from "@core/models/table_state/table-state";
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  atLocalTimeIso,
  endOfLocalDayIso,
  normalizeDateTimeString,
  startOfLocalDayIso,
  toFilterDisplay
} from "@utils/date-format.utils";
import { filterMatchTooltip, inlineFilterHint } from "@utils/filter-hint.utils";
import { exactMatch } from "@utils/filter.utils";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { ClockDialComponent, ClockTime, formatClockTime } from "@components/shared/clock-dial/clock-dial.component";
import { hasModifierKey } from "@angular/cdk/keycodes";
import {
  createFlexibleConnectedPositionStrategy,
  createOverlayRef,
  createRepositionScrollStrategy,
  ConnectedPosition,
  OverlayConfig,
  OverlayRef
} from "@angular/cdk/overlay";
import { TemplatePortal } from "@angular/cdk/portal";
import { TruncationTooltipDirective } from "@components/shared/directives/truncation-tooltip.directive";
import { FilterByLabelPipe } from "@components/shared/pipes/aria-label.pipe";
import { TooltipAriaLabelDirective } from "@components/shared/directives/tooltip-aria-label.directive";

function sameLocalDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/**
 * Where the time mode's clock popup goes, relative to the range picker panel: directly below it, else right of it,
 * else left of it, there centred on the clicked day's row (`offsetY` from the panel's centre), as a last resort above
 * the panel. Below or beside the panel it covers neither the calendar nor the summary line under it.
 */
export function clockPopupPositions(offsetY: number): ConnectedPosition[] {
  return [
    { originX: "center", originY: "bottom", overlayX: "center", overlayY: "top", offsetY: 4 },
    { originX: "end", originY: "center", overlayX: "start", overlayY: "center", offsetX: 8, offsetY },
    { originX: "start", originY: "center", overlayX: "end", overlayY: "center", offsetX: -8, offsetY },
    { originX: "center", originY: "top", overlayX: "center", overlayY: "bottom", offsetY: -4 }
  ];
}

function formatDay(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/** What the clock popup of the range picker's time mode picks: the time of the start or end bound on `day`. */
export interface AuditClockTarget {
  bound: "start" | "end";
  day: Date;
  // The earliest time the clock offers (the start time, for an end on the start day), or null for any.
  min: ClockTime | null;
}

type AuditCellRenderType =
  | "status-span"
  | "highlight-ok"
  | "date"
  | "policies-csv"
  | "copy-filter-text"
  | "serial-link"
  | "container-link"
  | "user-link"
  | "default";

const cellRenderTypeByKey: Record<string, AuditCellRenderType> = {
  success: "status-span",
  authentication: "status-span",
  sig_check: "highlight-ok",
  missing_line: "highlight-ok",
  startdate: "date",
  date: "date",
  policies: "policies-csv",
  serial: "serial-link",
  container_serial: "container-link",
  user: "user-link",
  action: "copy-filter-text",
  action_detail: "copy-filter-text",
  info: "copy-filter-text",
  user_agent: "copy-filter-text",
  privacyidea_server: "copy-filter-text",
  realm: "copy-filter-text",
  administrator: "copy-filter-text",
  client: "copy-filter-text",
  resolver: "copy-filter-text"
};

// A clicked cell value names one entry, so it is matched in full - except a policy, which is one of several the column
// lists.
const PARTIAL_MATCH_CELL_FILTER_KEYS = new Set(["policies"]);

// A clicked date cell filters the day the cell shows, in the viewer's zone, as a startdate interval. The day's
// text prefix would be the UTC day for an entry stored with +00:00.
const LOCAL_DAY_CELL_FILTER_KEYS = new Set(["startdate", "date"]);

// width: the col-width-* tier (see --column-width-* in styles.scss) each column's cell is fixed
// to. Columns left without a "width" stay flexible (long free text or a list that can overflow);
// the ones that do have a tier and their combined sizes (see table-width() in table.scss) drive
// the table's min-width in audit.component.scss.
const columnKeysMap: { key: string; label: string; width?: "s" | "m" | "l" | "xl" }[] = [
  { key: "number", label: $localize`:@@audit.number:Number`, width: "s" },
  { key: "action", label: $localize`:@@common.action:Action`, width: "l" },
  { key: "success", label: $localize`:@@common.successLabel:Success`, width: "s" },
  { key: "authentication", label: $localize`:@@audit.authentication:Authentication`, width: "m" },
  { key: "serial", label: $localize`:@@common.serial:Serial`, width: "m" },
  { key: "container_serial", label: $localize`:@@common.containerSerial:Container Serial`, width: "m" },
  { key: "startdate", label: $localize`:@@audit.startDate:Start Date`, width: "l" },
  { key: "duration", label: $localize`:@@audit.duration:Duration`, width: "s" },
  { key: "token_type", label: $localize`:@@common.tokenType:Token Type`, width: "s" },
  { key: "user", label: $localize`:@@common.user:User`, width: "s" },
  { key: "realm", label: $localize`:@@common.realm:Realm`, width: "s" },
  { key: "administrator", label: $localize`:@@common.administrator:Administrator`, width: "m" },
  { key: "action_detail", label: $localize`:@@audit.actionDetail:Action Detail` },
  { key: "info", label: $localize`:@@audit.info:Info` },
  { key: "policies", label: $localize`:@@common.policies:Policies` },
  { key: "client", label: $localize`:@@common.client:Client`, width: "s" },
  { key: "user_agent", label: $localize`:@@common.userAgent:User Agent`, width: "l" },
  { key: "user_agent_version", label: $localize`:@@audit.userAgentVersion:User Agent Version`, width: "s" },
  { key: "privacyidea_server", label: $localize`:@@audit.privacyideaServer:PrivacyIDEA Server`, width: "m" },
  { key: "log_level", label: $localize`:@@audit.logLevel:Log Level`, width: "s" },
  { key: "clearance_level", label: $localize`:@@audit.clearanceLevel:Clearance Level`, width: "s" },
  { key: "sig_check", label: $localize`:@@audit.signatureCheck:Signature Check`, width: "s" },
  { key: "missing_line", label: $localize`:@@audit.missingLine:Missing Line`, width: "s" },
  { key: "resolver", label: $localize`:@@common.resolver:Resolver`, width: "s" },
  { key: "thread_id", label: $localize`:@@audit.threadId:Thread ID`, width: "m" },
  { key: "container_type", label: $localize`:@@common.containerType:Container Type`, width: "s" }
];

@Component({
  selector: "app-audit",
  imports: [
    TooltipAriaLabelDirective,
    FilterByLabelPipe,
    InfoHintComponent,
    MatSuffix,
    RefocusAfterReloadDirective,
    FilterAutocompleteDirective,
    MatCardModule,
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
    ClearableInputComponent,
    MatIcon,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    ScrollEdgesDirective,
    DatePipe,
    TableStateComponent,
    PaginatorPageSizeTooltipDirective,
    PaginatorCompactRangeDirective,
    TruncationTooltipDirective,
    MatDatepickerModule,
    ClockDialComponent
  ],
  providers: [
    provideNativeDateAdapter(),
    AuditRangeSelectionStrategy,
    { provide: MAT_DATE_RANGE_SELECTION_STRATEGY, useExisting: AuditRangeSelectionStrategy }
  ],
  templateUrl: "./audit.component.html",
  styleUrl: "./audit.component.scss"
})
export class AuditComponent {
  readonly columnKeysMap = columnKeysMap;
  readonly columnKeys: string[] = this.columnKeysMap.map((column) => column.key);
  protected readonly auditService: AuditServiceInterface = inject(AuditService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  readonly apiFilterKeyMap = this.auditService.apiFilterKeyMap;
  readonly filterHint = inlineFilterHint();
  readonly filterMatchInfo = computed(() =>
    filterMatchTooltip(
      $localize`:@@nav.audit:Audit`,
      [...this.auditService.apiFilterKeys, ...this.auditService.advancedApiFilterKeys],
      (key) => this.auditService.exactMatchKeys.has(key)
    )
  );
  sort = this.auditService.sort;

  @ViewChild("filterHTMLInputElement", { static: false })
  filterInput!: ElementRef<HTMLInputElement>;

  totalLength: WritableSignal<number> = linkedSignal({
    source: () => (this.auditService.auditResource.hasValue() ? this.auditService.auditResource.value() : undefined),
    computation: (auditResource, previous) => {
      return auditResource?.result?.value?.count ?? previous?.value ?? 0;
    }
  });
  auditDataSource: WritableSignal<MatTableDataSource<AuditData>> = linkedSignal({
    source: () => (this.auditService.auditResource.hasValue() ? this.auditService.auditResource.value() : undefined),
    computation: (auditResource, previous) => {
      if (auditResource) {
        return new MatTableDataSource(auditResource.result?.value?.auditdata);
      }
      // A reload in flight clears the resource value before the new response arrives - keep
      // showing the previous rows instead of flashing empty, now that the table itself stays
      // mounted through a reload (see TableState.lastKnownCount).
      return previous?.value ?? new MatTableDataSource<AuditData>([]);
    }
  });
  readonly tableState = new TableState({
    resource: this.auditService.auditResource,
    count: () => this.totalLength(),
    filterActive: () => !this.auditService.activeFilter().isEmpty,
    allowed: () => this.authService.actionAllowed("auditlog"),
    resetFilter: () => this.auditService.clearFilter()
  });
  basePageSizeOptions = [...this.tableUtilsService.pageSizeOptions()];
  pageSizeOptions = computed(() => {
    if (!this.basePageSizeOptions.includes(this.auditService.pageSize())) {
      this.basePageSizeOptions.push(this.auditService.pageSize());
      this.basePageSizeOptions.sort((a, b) => a - b);
    }
    return this.basePageSizeOptions;
  });

  onPageEvent(event: PageEvent) {
    this.auditService.pageSize.set(event.pageSize);
    this.auditService.pageIndex.set(event.pageIndex + 1);
  }

  toggleFilter(filterKeyword: string): void {
    this.auditService.updateFilter((current) =>
      filterKeyword === "success"
        ? this.tableUtilsService.toggleBooleanInFilter({
            keyword: filterKeyword,
            currentValue: current
          })
        : this.tableUtilsService.toggleKeywordInFilter({
            keyword: filterKeyword,
            currentValue: current
          })
    );
  }

  isFilterSelected(filter: string, inputValue: FilterValue): boolean {
    return inputValue.hasKey(filter);
  }

  getFilterIconName(keyword: string): string {
    if (keyword === "success") {
      const value = this.auditService.activeFilter().booleanValueOfKey(keyword);
      if (value === undefined) {
        return "filter_alt";
      }
      return value ? "screen_rotation_alt" : "filter_alt_off";
    } else {
      const isSelected = this.auditService.activeFilter().hasKey(keyword);
      return isSelected ? "filter_alt_off" : "filter_alt";
    }
  }

  onKeywordClick(filterKeyword: string): void {
    this.toggleFilter(filterKeyword);
    this.filterInput?.nativeElement.focus();
  }

  protected readonly rangeHeader = AuditDateRangeHeaderComponent;
  readonly rangePicker = viewChild<MatDateRangePicker<Date>>("rangePicker");

  // The date column's filter button opens the range picker, every other column toggles its keyword filter.
  onHeaderFilterClick(columnKey: string): void {
    if (columnKey === "startdate") {
      this.rangePicker()?.open();
      return;
    }
    this.onKeywordClick(this.apiFilterKeyMap[columnKey]);
  }

  getCellRenderType(columnKey: string): AuditCellRenderType {
    return cellRenderTypeByKey[columnKey] ?? "default";
  }

  // info is free prose that practically never repeats, so filtering on one entry's value finds only that entry.
  showInlineCellFilter(columnKey: string): boolean {
    return columnKey !== "info";
  }

  // The range picker shows the local days of the active range, and is empty without one.
  readonly rangePickerStart = computed<Date | null>(() => {
    const fromIso = this.auditService.timestampFrom();
    return fromIso ? new Date(fromIso) : null;
  });
  readonly rangePickerEnd = computed<Date | null>(() => {
    const toIso = this.auditService.timestampTo();
    return toIso ? new Date(toIso) : null;
  });
  // The range on the picker button in the viewer's locale, or null to show the neutral "Date range" label.
  // Choosing a date sets the whole local day as that bound (inclusive) and keeps the other bound, clearing a field
  // (null) drops its bound.
  onRangeStartDateChange(date: Date | null): void {
    if (date) {
      this.startPickedInSession.set(true);
    }
    this.applyTimeRange(date ? startOfLocalDayIso(date) : null, this.auditService.timestampTo());
  }

  onRangeEndDateChange(date: Date | null): void {
    this.applyTimeRange(this.auditService.timestampFrom(), date ? endOfLocalDayIso(date) : null);
  }

  // Whether a start day (in time mode: a start time) was picked since the picker opened. Only such a pick makes the
  // close rules below apply, so opening and closing the picker leaves an open-ended range as it is.
  private readonly startPickedInSession = signal<boolean>(false);

  // Picking a single day and dismissing the picker leaves the end open. That means "this one day", so the end is set
  // to the end of the start day instead of leaving an open-ended range. In time mode, a start day with a picked start
  // time and no end yet runs from that time to the end of its day (rule 1), however the picker was closed. Both rules
  // apply only to a start picked in this picker session, an open-ended range the picker opened with stays open.
  onRangePickerClosed(): void {
    const timedStart = this.timedStart();
    const endPicked = !!this.timedEnd()?.time;
    const startPicked = this.startPickedInSession();
    this.startPickedInSession.set(false);
    this.resetTimedSelection();
    if (!startPicked) {
      return;
    }
    if (timedStart?.time && !endPicked) {
      this.applyTimeRange(
        atLocalTimeIso(timedStart.day, formatClockTime(timedStart.time)),
        endOfLocalDayIso(timedStart.day)
      );
    }
    const start = this.rangePickerStart();
    if (start && !this.auditService.timestampTo()) {
      this.applyTimeRange(this.auditService.timestampFrom(), endOfLocalDayIso(start));
    }
  }

  onRangePickerOpened(): void {
    this.startPickedInSession.set(false);
    this.resetTimedSelection();
  }

  // Time mode (the header's "Time" checkbox): every day click opens a clock dial in a popup at the clicked cell, and the
  // picker shows an actions row (the summary of what is picked). With actions registered the picker keeps clicked days in a pending copy
  // of its model and neither applies nor closes on a complete range (MatDatepickerContent._handleUserSelection), so it
  // stays open while the end clock is shown. The range is applied here, through applyTimeRange, never by the picker:
  // rule 1, one day: its start time to the end of that day, applied when the picker closes (also by Escape, see
  // onTimedSelectionAborted).
  // rule 2, the start day clicked again after its start time: the end clock on that day, earlier times disabled.
  // rule 3, a later day: the end clock on that day. The end minute applies the range and closes the picker.
  // The self-service log has no range picker and does not provide the strategy.
  private readonly rangeSelection = inject(AuditRangeSelectionStrategy, { optional: true });
  private readonly injector = inject(Injector);
  private readonly viewContainerRef = inject(ViewContainerRef);
  readonly rangeTimeMode = this.auditService.rangeTimeMode;
  readonly clockPopup = viewChild<TemplateRef<unknown>>("clockPopup");
  // The clicked start and end day, each with its time once picked on the clock.
  private readonly timedStart = signal<{ day: Date; time: ClockTime | null } | null>(null);
  private readonly timedEnd = signal<{ day: Date; time: ClockTime | null } | null>(null);
  // What the open clock picks, or null when no clock is open.
  readonly clockTarget = signal<AuditClockTarget | null>(null);
  readonly clockLabel = computed(() =>
    this.clockTarget()?.bound === "end"
      ? $localize`:@@audit.rangeEndTime:End time`
      : $localize`:@@audit.rangeStartTime:Start time`
  );
  // Shown under the calendar: what is picked so far ("yyyy-MM-dd HH:mm", local, like the table), so the user sees the
  // time was taken.
  // Both lines are always there in time mode, "–" until the day is clicked and "--:--" (as on the clock) until the
  // time is picked, so the row neither starts out empty nor changes height while picking.
  readonly rangeSummary = computed<string[]>(() =>
    (
      [
        [this.timedStart(), $localize`:@@audit.rangeSummaryStart:Start`],
        [this.timedEnd(), $localize`:@@audit.rangeSummaryEnd:End`]
      ] as const
    ).map(([bound, label]) =>
      bound
        ? `${label}: ${formatDay(bound.day)} ${bound.time ? formatClockTime(bound.time) : "--:--"}`
        : `${label}: –`
    )
  );
  private clockOverlay: OverlayRef | null = null;
  private clockAnchor: HTMLElement | null = null;

  constructor() {
    // The strategy routes day clicks here while time mode is on.
    if (this.rangeSelection) {
      this.rangeSelection.interceptor = {
        active: () => this.rangeTimeMode(),
        dayClick: (date, event) => (date ? this.onTimedDayClick(date, event) : this.onTimedSelectionAborted())
      };
    }
    // Switching time mode while the picker is open swaps its model (pending copy or live), so a half-picked time
    // selection is dropped.
    effect(() => {
      this.rangeTimeMode();
      untracked(() => this.resetTimedSelection());
    });
    inject(DestroyRef).onDestroy(() => this.closeClock());
  }

  // The time a clock emitted: a start time waits for the end day (or the picker closing), an end time applies the
  // range from the start time to the end time, both at second 0, and closes the picker. A picked time is a point in
  // time, the backend includes the whole second of an end given in whole seconds.
  onClockTimeSelected(time: ClockTime): void {
    const target = this.clockTarget();
    const timedStart = this.timedStart();
    this.closeClock();
    if (!target || !timedStart) {
      return;
    }
    if (target.bound === "start") {
      this.startPickedInSession.set(true);
      this.timedStart.set({ day: timedStart.day, time });
      return;
    }
    // The picked selection stays (for the summary) until the picker has closed, the end time keeps the close handler
    // from applying rule 1 over it.
    this.timedEnd.set({ day: target.day, time });
    const fromIso = atLocalTimeIso(timedStart.day, formatClockTime(timedStart.time!));
    const toIso = atLocalTimeIso(target.day, formatClockTime(time));
    this.applyTimeRange(fromIso, toIso);
    this.rangePicker()?.close();
  }

  // A day click in time mode. After a picked start time, the start day or a later one is the end day, anything else
  // (no start yet, no start time yet, an earlier day) starts over with that day as the start. Returns the selection
  // the calendar shows.
  private onTimedDayClick(date: Date, event: Event | undefined): DateRange<Date> {
    const anchor = (event?.target as Element | null | undefined)?.closest<HTMLElement>(".mat-calendar-body-cell") ?? null;
    const timedStart = this.timedStart();
    if (timedStart?.time && startOfLocalDayIso(date) >= startOfLocalDayIso(timedStart.day)) {
      const min = sameLocalDay(date, timedStart.day) ? timedStart.time : null;
      this.timedEnd.set({ day: date, time: null });
      this.openClock({ bound: "end", day: date, min }, anchor);
      return new DateRange<Date>(timedStart.day, date);
    }
    this.timedStart.set({ day: date, time: null });
    this.timedEnd.set(null);
    this.openClock({ bound: "start", day: date, min: null }, anchor);
    return new DateRange<Date>(date, null);
  }

  // Escape on the calendar while its range preview is shown (a hovered day, or the focus on a day cell, which the clock
  // hands back to the clicked cell) makes the month view report a null selection and stop the event, so the picker
  // overlay never sees it. Without the preview Escape reaches the overlay and closes the picker. Closing it here too
  // makes Escape behave the same either way: with a picked start time rule 1 applies, without one nothing does.
  private onTimedSelectionAborted(): DateRange<Date> {
    const timedStart = this.timedStart();
    this.closeClock();
    this.rangePicker()?.close();
    return new DateRange<Date>(timedStart?.day ?? null, null);
  }

  // The clock's overlay origin is the picker panel, so it opens below the calendar, or beside it level with the clicked
  // day's row.
  clockPopupPositioning(anchor: HTMLElement): { origin: HTMLElement; positions: ConnectedPosition[] } {
    const panel = anchor.closest<HTMLElement>(".mat-datepicker-content") ?? anchor;
    const cell = anchor.getBoundingClientRect();
    const box = panel.getBoundingClientRect();
    const offsetY = Math.round(cell.top + cell.height / 2 - (box.top + box.height / 2));
    return { origin: panel, positions: clockPopupPositions(offsetY) };
  }

  // Shows the clock in a popup below the picker panel, or beside it at the clicked day's row (see clockPopupPositions),
  // pushed back into the viewport if none fits. Its backdrop and Escape close only the clock, the picker stays open,
  // and the focus goes back to the clicked day. The clock traps the focus while it is shown.
  private openClock(target: AuditClockTarget, anchor: HTMLElement | null): void {
    this.closeClock();
    this.clockTarget.set(target);
    const template = this.clockPopup();
    if (!template || !anchor) {
      return;
    }
    const { origin, positions } = this.clockPopupPositioning(anchor);
    const positionStrategy = createFlexibleConnectedPositionStrategy(this.injector, origin)
      .withPositions(positions)
      .withFlexibleDimensions(false)
      .withPush(true)
      .withViewportMargin(8);
    const overlayRef = createOverlayRef(
      this.injector,
      new OverlayConfig({
        positionStrategy,
        hasBackdrop: true,
        backdropClass: "cdk-overlay-transparent-backdrop",
        scrollStrategy: createRepositionScrollStrategy(this.injector)
      })
    );
    overlayRef.backdropClick().subscribe(() => this.closeClock());
    overlayRef.keydownEvents().subscribe((event) => {
      if (event.key === "Escape" && !hasModifierKey(event)) {
        event.preventDefault();
        this.closeClock();
      }
    });
    overlayRef.attach(new TemplatePortal(template, this.viewContainerRef));
    this.clockOverlay = overlayRef;
    this.clockAnchor = anchor;
  }

  // Closes the clock popup, if open, and gives the focus back to the day cell it was opened from.
  private closeClock(): void {
    const anchor = this.clockAnchor;
    this.clockOverlay?.dispose();
    this.clockOverlay = null;
    this.clockAnchor = null;
    this.clockTarget.set(null);
    if (anchor?.isConnected) {
      anchor.focus();
    }
  }

  private resetTimedSelection(): void {
    this.closeClock();
    this.timedStart.set(null);
    this.timedEnd.set(null);
  }

  // Inline "filter by this value" action on a cell: replaces whatever the column was filtered by with this value.
  addFilterValue(columnKey: string, value: string): void {
    if (LOCAL_DAY_CELL_FILTER_KEYS.has(columnKey)) {
      this.filterLocalDay(value);
      return;
    }
    const keyword = this.apiFilterKeyMap[columnKey] ?? columnKey;
    const filterValue = PARTIAL_MATCH_CELL_FILTER_KEYS.has(keyword) ? value : exactMatch(value);
    this.auditService.updateFilter((current) => current.addEntry(keyword, filterValue));
  }

  private filterLocalDay(timestamp: string): void {
    const shown = new Date(normalizeDateTimeString(timestamp));
    if (Number.isNaN(shown.getTime())) {
      return;
    }
    this.applyTimeRange(startOfLocalDayIso(shown), endOfLocalDayIso(shown));
  }

  // Single writer of the time range: sets the bounds the request is built from and mirrors them into the filter text
  // as the startdate chip "<from>/<to>" with the viewer's offset, a null bound left empty. It replaces a typed text
  // filter on startdate. Without both bounds the chip and its parameter are removed.
  private applyTimeRange(fromIso: string | null, toIso: string | null): void {
    this.auditService.timestampFrom.set(fromIso);
    this.auditService.timestampTo.set(toIso);
    this.auditService.updateFilter((current) =>
      fromIso || toIso
        ? current.addEntry(
            "startdate",
            `${fromIso ? toFilterDisplay(fromIso) : ""}/${toIso ? toFilterDisplay(toIso) : ""}`
          )
        : current.removeKey("startdate")
    );
  }
}
