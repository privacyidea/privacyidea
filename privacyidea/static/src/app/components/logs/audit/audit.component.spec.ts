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
import { DateRange } from "@angular/material/datepicker";
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatPaginator } from "@angular/material/paginator";
import { MatTableDataSource } from "@angular/material/table";
import { By } from "@angular/platform-browser";
import { ActivatedRoute } from "@angular/router";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { AuditData, AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import {
  MockAuditService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { MockTableUtilsService } from "@testing/mock-services/mock-table-utils-service";
import { endOfLocalDayIso, startOfLocalDayIso, toFilterDisplay } from "@utils/date-format.utils";
import { of } from "rxjs";
import { AuditComponent, clockPopupPositions } from "./audit.component";
import { AuditSelfServiceComponent } from "./audit.self-service.component";
import { axe } from "@testing/axe";

describe("AuditComponent (unit)", () => {
  let fixture: ComponentFixture<AuditComponent>;
  let component: AuditComponent;
  let mockAuditService: MockAuditService;
  let mockTableUtilsService: MockTableUtilsService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    TestBed.overrideComponent(AuditComponent, {
      set: {
        template: "<div></div>",
        animations: []
      }
    });

    TestBed.overrideComponent(AuditSelfServiceComponent, {
      set: {
        template: "<div></div>",
        animations: []
      }
    });

    await TestBed.configureTestingModule({
      imports: [AuditComponent],
      providers: [
        provideHttpClient(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: MockAuditService, useClass: MockAuditService },
        { provide: MockTableUtilsService, useClass: MockTableUtilsService },
        { provide: MockContentService, useClass: MockContentService },
        { provide: MockAuthService, useClass: MockAuthService },
        { provide: AuditService, useExisting: MockAuditService },
        { provide: TableUtilsService, useExisting: MockTableUtilsService },
        { provide: ContentService, useExisting: MockContentService },
        { provide: AuthService, useExisting: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    jest.useFakeTimers();

    fixture = TestBed.createComponent(AuditComponent);
    component = fixture.componentInstance;
    mockAuditService = TestBed.inject(MockAuditService);
    mockTableUtilsService = TestBed.inject(MockTableUtilsService);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "auditlog"
    });
  });

  it("creates", () => {
    expect(component).toBeTruthy();
    expect(component.columnKeys.length).toBe(component.columnKeysMap.length);
  });

  it("creates self service", () => {
    const selfFixture = TestBed.createComponent(AuditSelfServiceComponent);
    expect(selfFixture.componentInstance).toBeTruthy();
  });

  describe("inline cell filter", () => {
    it("filters by the API keyword the column maps to", () => {
      component.apiFilterKeyMap["realm"] = "realm_name";

      component.addFilterValue("realm", "defrealm");

      expect(mockAuditService.activeFilter().getValueOfKey("realm_name")).toBe("=defrealm");
      expect(mockAuditService.activeFilter().hasKey("realm")).toBe(false);
    });

    it("filters by the column key itself when it has no API mapping", () => {
      mockAuditService.activeFilter.set(new FilterValue({ value: "serial: OLD" }));

      component.addFilterValue("serial", "HOTP1");

      expect(mockAuditService.activeFilter().getValueOfKey("serial")).toBe("=HOTP1");
    });

    it("keeps a policy a partial match", () => {
      component.addFilterValue("policies", "otp");

      expect(mockAuditService.activeFilter().getValueOfKey("policies")).toBe("otp");
    });

    it("date cell filter selects the local day as range", () => {
      // Shortly after midnight UTC: in most zones the local day the cell shows differs from the UTC day.
      const cellValue = "2026-09-25T00:30:00.000000+00:00";
      const shown = new Date(cellValue);
      const fromIso = new Date(shown.getFullYear(), shown.getMonth(), shown.getDate(), 0, 0, 0, 0).toISOString();
      const toIso = new Date(shown.getFullYear(), shown.getMonth(), shown.getDate(), 23, 59, 59, 0).toISOString();

      component.addFilterValue("startdate", cellValue);

      expect(mockAuditService.timestampFrom()).toBe(fromIso);
      expect(mockAuditService.timestampTo()).toBe(toIso);
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(
        `${toFilterDisplay(fromIso)}/${toFilterDisplay(toIso)}`
      );
    });
  });

  describe("date range", () => {
    it("range picker sets the startdate chip and service signals", () => {
      const firstDay = new Date(2026, 8, 24);
      const lastDay = new Date(2026, 8, 25);
      const fromIso = new Date(2026, 8, 24, 0, 0, 0, 0).toISOString();
      const toIso = new Date(2026, 8, 25, 23, 59, 59, 0).toISOString();
      // There is one startdate chip, so the range replaces a typed text filter on it.
      mockAuditService.activeFilter.set(new FilterValue({ value: "startdate: 2026-09" }));

      component.onRangeStartDateChange(firstDay);
      component.onRangeEndDateChange(lastDay);

      expect(mockAuditService.timestampFrom()).toBe(fromIso);
      expect(mockAuditService.timestampTo()).toBe(toIso);
      // The chip carries the bounds as an interval in the viewer's zone with its offset.
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(
        `${toFilterDisplay(fromIso)}/${toFilterDisplay(toIso)}`
      );
      expect(mockAuditService.activeFilter().hasKey("start_time")).toBe(false);
      expect(mockAuditService.activeFilter().hasKey("end_time")).toBe(false);
      expect(toFilterDisplay(fromIso)).toMatch(/ (Z|[+-]\d{2}:\d{2})$/);
    });

    it("closing the picker with only a start date filters exactly that one day", () => {
      const day = new Date(2026, 8, 24);
      component.onRangeStartDateChange(day);
      component.onRangeEndDateChange(null);
      expect(mockAuditService.timestampTo()).toBeNull();

      component.onRangePickerClosed();

      expect(mockAuditService.timestampTo()).toBe(endOfLocalDayIso(day));
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(
        `${toFilterDisplay(startOfLocalDayIso(day))}/${toFilterDisplay(endOfLocalDayIso(day))}`
      );
    });

    it("opening and closing the picker without a pick keeps an open-ended range open", () => {
      const fromIso: string = startOfLocalDayIso(new Date(2026, 8, 24));
      const chip = `${toFilterDisplay(fromIso)}/`;
      mockAuditService.timestampFrom.set(fromIso);
      mockAuditService.activeFilter.set(new FilterValue().addEntry("startdate", chip));

      component.onRangePickerOpened();
      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(fromIso);
      expect(mockAuditService.timestampTo()).toBeNull();
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(chip);
    });

    it("a start day picked after opening over an open-ended range still filters that whole day on close", () => {
      const day: Date = new Date(2026, 8, 26);
      mockAuditService.timestampFrom.set(startOfLocalDayIso(new Date(2026, 8, 24)));

      component.onRangePickerOpened();
      component.onRangeStartDateChange(day);
      component.onRangeEndDateChange(null);
      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(startOfLocalDayIso(day));
      expect(mockAuditService.timestampTo()).toBe(endOfLocalDayIso(day));
    });

    it("closing the picker with a full range changes nothing", () => {
      component.onRangeStartDateChange(new Date(2026, 8, 24));
      component.onRangeEndDateChange(new Date(2026, 8, 26));
      const from = mockAuditService.timestampFrom();
      const to = mockAuditService.timestampTo();

      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(from);
      expect(mockAuditService.timestampTo()).toBe(to);
    });

    it("header clear button drops the startdate range and closes the picker", () => {
      component.onRangeStartDateChange(new Date(2026, 8, 24));
      component.onRangeEndDateChange(new Date(2026, 8, 25));
      // The stock calendar header needs a real MatCalendar, so the component is built without rendering it.
      const header = TestBed.runInInjectionContext(() => new AuditDateRangeHeaderComponent());
      expect(header.hasRange()).toBe(true);

      header.clear();

      expect(mockAuditService.timestampFrom()).toBeNull();
      expect(mockAuditService.timestampTo()).toBeNull();
      expect(mockAuditService.activeFilter().hasKey("startdate")).toBe(false);
      expect(header.hasRange()).toBe(false);
    });
  });

  describe("date range with time (header checkbox on)", () => {
    let strategy: AuditRangeSelectionStrategy;
    // A click on a calendar day, the way the calendar hands it to the range strategy.
    const clickDay = (day: Date) =>
      strategy.selectionFinished(day, new DateRange<Date>(null, null), new MouseEvent("click"));

    beforeEach(() => {
      strategy = fixture.debugElement.injector.get(AuditRangeSelectionStrategy);
    });

    it("header checkbox switches time mode on and off, default off", () => {
      const header = TestBed.runInInjectionContext(() => new AuditDateRangeHeaderComponent());
      expect(header.timeMode()).toBe(false);

      header.onTimeModeChange(true);
      expect(mockAuditService.rangeTimeMode()).toBe(true);
      expect(component.rangeTimeMode()).toBe(true);

      header.onTimeModeChange(false);
      expect(mockAuditService.rangeTimeMode()).toBe(false);
    });

    it("checkbox off: a day click builds the stock range, opens no clock and applies whole local days", () => {
      const first = clickDay(new Date(2026, 8, 24));
      expect(first.start).toEqual(new Date(2026, 8, 24));
      expect(first.end).toBeNull();
      const second = strategy.selectionFinished(new Date(2026, 8, 25), first, new MouseEvent("click"));
      expect(second.end).toEqual(new Date(2026, 8, 25));
      expect(component.clockTarget()).toBeNull();
      expect(strategy.createDrag(new Date(2026, 8, 24), second, new Date(2026, 8, 23))).not.toBeNull();

      component.onRangeStartDateChange(new Date(2026, 8, 24));
      component.onRangeEndDateChange(new Date(2026, 8, 25));

      expect(mockAuditService.timestampFrom()).toBe(new Date(2026, 8, 24, 0, 0, 0, 0).toISOString());
      expect(mockAuditService.timestampTo()).toBe(new Date(2026, 8, 25, 23, 59, 59, 0).toISOString());
    });

    it("rule 1: one clicked day opens the start clock, closing the picker applies the start time to that day's end", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();

      const range = clickDay(new Date(2026, 8, 24));
      expect(range.start).toEqual(new Date(2026, 8, 24));
      expect(range.end).toBeNull();
      expect(component.clockTarget()).toEqual({ bound: "start", day: new Date(2026, 8, 24), min: null });

      component.onClockTimeSelected({ hour: 8, minute: 30 });
      expect(component.clockTarget()).toBeNull();
      // Nothing is applied while the picker is open: a second click could still choose an end.
      expect(mockAuditService.timestampFrom()).toBeNull();

      component.onRangePickerClosed();

      const fromIso = new Date(2026, 8, 24, 8, 30, 0, 0).toISOString();
      const toIso = new Date(2026, 8, 24, 23, 59, 59, 0).toISOString();
      expect(mockAuditService.timestampFrom()).toBe(fromIso);
      expect(mockAuditService.timestampTo()).toBe(toIso);
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(
        `${toFilterDisplay(fromIso)}/${toFilterDisplay(toIso)}`
      );
    });

    it("opening and closing the picker without a pick keeps an open-ended range open", () => {
      const fromIso: string = startOfLocalDayIso(new Date(2026, 8, 24));
      const chip = `${toFilterDisplay(fromIso)}/`;
      mockAuditService.rangeTimeMode.set(true);
      mockAuditService.timestampFrom.set(fromIso);
      mockAuditService.activeFilter.set(new FilterValue().addEntry("startdate", chip));

      component.onRangePickerOpened();
      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(fromIso);
      expect(mockAuditService.timestampTo()).toBeNull();
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(chip);
    });

    it("the first day after reopening over an active range starts a new range, the second sets its end", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      mockAuditService.timestampFrom.set(new Date(2026, 8, 20, 8, 30, 0, 0).toISOString());
      mockAuditService.timestampTo.set(new Date(2026, 8, 22, 18, 45, 0, 0).toISOString());
      component.onRangePickerOpened();
      // The seeded range is shown until the first click.
      expect(component.rangeSummary()).toEqual(["Start: 2026-09-20 08:30", "End: 2026-09-22 18:45"]);

      const first = clickDay(new Date(2026, 8, 24));
      expect(first.start).toEqual(new Date(2026, 8, 24));
      expect(first.end).toBeNull();
      expect(component.clockTarget()).toEqual({ bound: "start", day: new Date(2026, 8, 24), min: null });
      expect(component.clockLabel()).toBe("Start time");
      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 --:--", "End: –"]);
      component.onClockTimeSelected({ hour: 9, minute: 0 });

      const second = clickDay(new Date(2026, 8, 26));
      expect(second.start).toEqual(new Date(2026, 8, 24));
      expect(second.end).toEqual(new Date(2026, 8, 26));
      expect(component.clockTarget()).toEqual({ bound: "end", day: new Date(2026, 8, 26), min: null });
      expect(component.clockLabel()).toBe("End time");
      component.onClockTimeSelected({ hour: 17, minute: 15 });

      expect(mockAuditService.timestampFrom()).toBe(new Date(2026, 8, 24, 9, 0, 0, 0).toISOString());
      expect(mockAuditService.timestampTo()).toBe(new Date(2026, 8, 26, 17, 15, 0, 0).toISOString());
    });

    it("the first day after reopening over an open-ended range starts a new range", () => {
      mockAuditService.rangeTimeMode.set(true);
      mockAuditService.timestampFrom.set(startOfLocalDayIso(new Date(2026, 8, 20)));
      TestBed.tick();
      component.onRangePickerOpened();

      const range = clickDay(new Date(2026, 8, 24));
      expect(range.start).toEqual(new Date(2026, 8, 24));
      expect(range.end).toBeNull();
      expect(component.clockLabel()).toBe("Start time");
    });

    it("closing the picker before a start time was picked applies the clicked day as a whole day", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));

      component.onRangePickerClosed();

      expect(component.clockTarget()).toBeNull();
      expect(mockAuditService.timestampFrom()).toBe(startOfLocalDayIso(new Date(2026, 8, 24)));
      expect(mockAuditService.timestampTo()).toBe(endOfLocalDayIso(new Date(2026, 8, 24)));
    });

    it("a new start day without a time replaces the applied range with that whole day when the picker closes", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      mockAuditService.timestampFrom.set(new Date(2026, 10, 4, 8, 30, 0, 0).toISOString());
      mockAuditService.timestampTo.set(new Date(2026, 10, 7, 18, 45, 0, 0).toISOString());
      component.onRangePickerOpened();

      clickDay(new Date(2026, 10, 11));
      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(startOfLocalDayIso(new Date(2026, 10, 11)));
      expect(mockAuditService.timestampTo()).toBe(endOfLocalDayIso(new Date(2026, 10, 11)));
    });

    it("opening and closing the picker in time mode without a click keeps the applied range", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      const from = new Date(2026, 10, 4, 8, 30, 0, 0).toISOString();
      const to = new Date(2026, 10, 7, 18, 45, 0, 0).toISOString();
      mockAuditService.timestampFrom.set(from);
      mockAuditService.timestampTo.set(to);
      component.onRangePickerOpened();

      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(from);
      expect(mockAuditService.timestampTo()).toBe(to);
    });

    it("rule 2: the same day clicked again after the start time opens the end clock on that day", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));
      component.onClockTimeSelected({ hour: 8, minute: 30 });

      const range = clickDay(new Date(2026, 8, 24));
      expect(range.start).toEqual(new Date(2026, 8, 24));
      expect(range.end).toEqual(new Date(2026, 8, 24));
      // The end clock only offers times from the start time on.
      expect(component.clockTarget()).toEqual({
        bound: "end",
        day: new Date(2026, 8, 24),
        min: { hour: 8, minute: 30 }
      });

      component.onClockTimeSelected({ hour: 17, minute: 15 });

      const fromIso = new Date(2026, 8, 24, 8, 30, 0, 0).toISOString();
      const toIso = new Date(2026, 8, 24, 17, 15, 0, 0).toISOString();
      expect(mockAuditService.timestampFrom()).toBe(fromIso);
      expect(mockAuditService.timestampTo()).toBe(toIso);
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(
        `${toFilterDisplay(fromIso)}/${toFilterDisplay(toIso)}`
      );
      expect(component.clockTarget()).toBeNull();

      // The picker closing afterwards does not overwrite the applied end.
      component.onRangePickerClosed();
      expect(mockAuditService.timestampTo()).toBe(toIso);
    });

    it("rule 3: two different days get the start time on the first and the end time on the second", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));
      component.onClockTimeSelected({ hour: 22, minute: 0 });
      clickDay(new Date(2026, 8, 26));
      // A later day allows any end time.
      expect(component.clockTarget()).toEqual({ bound: "end", day: new Date(2026, 8, 26), min: null });

      component.onClockTimeSelected({ hour: 6, minute: 45 });

      expect(mockAuditService.timestampFrom()).toBe(new Date(2026, 8, 24, 22, 0, 0, 0).toISOString());
      expect(mockAuditService.timestampTo()).toBe(new Date(2026, 8, 26, 6, 45, 0, 0).toISOString());
    });

    it("a picked end time is that point in time: 12:00 to 13:00 ends at 13:00:00, not 13:00:59", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));
      component.onClockTimeSelected({ hour: 12, minute: 0 });
      clickDay(new Date(2026, 8, 24));

      component.onClockTimeSelected({ hour: 13, minute: 0 });

      const fromIso: string = new Date(2026, 8, 24, 12, 0, 0, 0).toISOString();
      const toIso: string = new Date(2026, 8, 24, 13, 0, 0, 0).toISOString();
      expect(mockAuditService.timestampTo()).toBe(toIso);
      expect(mockAuditService.activeFilter().getValueOfKey("startdate")).toBe(
        `${toFilterDisplay(fromIso)}/${toFilterDisplay(toIso)}`
      );
      expect(toFilterDisplay(toIso)).toContain("13:00:00");
    });

    it("a day before the start day starts over with a new start clock", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));
      component.onClockTimeSelected({ hour: 8, minute: 30 });

      const range = clickDay(new Date(2026, 8, 20));

      expect(range.start).toEqual(new Date(2026, 8, 20));
      expect(range.end).toBeNull();
      expect(component.clockTarget()).toEqual({ bound: "start", day: new Date(2026, 8, 20), min: null });
      component.onRangePickerClosed();
      // The earlier start time belonged to the abandoned day, the new day without a time is applied as a whole day.
      expect(mockAuditService.timestampFrom()).toBe(startOfLocalDayIso(new Date(2026, 8, 20)));
      expect(mockAuditService.timestampTo()).toBe(endOfLocalDayIso(new Date(2026, 8, 20)));
    });

    it("a second click before the start time was picked moves the start instead of ending the range", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));

      const range = clickDay(new Date(2026, 8, 26));

      expect(range.start).toEqual(new Date(2026, 8, 26));
      expect(range.end).toBeNull();
      expect(component.clockTarget()?.bound).toBe("start");
    });

    it("summary under the calendar always shows start and end, with placeholders until they are picked", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      expect(component.rangeSummary()).toEqual(["Start: –", "End: –"]);

      clickDay(new Date(2026, 8, 24));
      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 --:--", "End: –"]);

      component.onClockTimeSelected({ hour: 8, minute: 30 });
      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 08:30", "End: –"]);

      clickDay(new Date(2026, 8, 26));
      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 08:30", "End: 2026-09-26 --:--"]);

      component.onClockTimeSelected({ hour: 18, minute: 45 });
      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 08:30", "End: 2026-09-26 18:45"]);
    });

    it("the hint names the next step: start day, start time, end day or close, end time", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      mockAuditService.timestampFrom.set(new Date(2026, 8, 20, 8, 30, 0, 0).toISOString());
      mockAuditService.timestampTo.set(new Date(2026, 8, 22, 18, 45, 0, 0).toISOString());
      component.onRangePickerOpened();
      // The seeded range is display only, so the first step is still the start day.
      expect(component.rangeHint()).toBe("Pick the start day");

      clickDay(new Date(2026, 8, 24));
      expect(component.rangeHint()).toBe("Pick the start time");

      component.onClockTimeSelected({ hour: 9, minute: 0 });
      expect(component.rangeHint()).toBe("Pick the end day, or close to filter this day");

      clickDay(new Date(2026, 8, 26));
      expect(component.rangeHint()).toBe("Pick the end time");

      component.onClockTimeSelected({ hour: 17, minute: 15 });
      expect(component.rangeHint()).toBe("");
    });

    it("reopening the picker on an applied range shows its times in the summary", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      mockAuditService.timestampFrom.set(new Date(2026, 8, 24, 8, 30, 0, 0).toISOString());
      mockAuditService.timestampTo.set(new Date(2026, 8, 26, 18, 45, 0, 0).toISOString());

      component.onRangePickerOpened();

      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 08:30", "End: 2026-09-26 18:45"]);
    });

    it("switching Time on in the open picker shows the active range in the summary", () => {
      mockAuditService.timestampFrom.set(new Date(2026, 8, 24, 8, 30, 0, 0).toISOString());
      mockAuditService.timestampTo.set(new Date(2026, 8, 26, 18, 45, 0, 0).toISOString());
      component.onRangePickerOpened();

      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      TestBed.tick();

      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 08:30", "End: 2026-09-26 18:45"]);
    });

    it("switching Time off after a seeded open drops the seeded start, so a day pick runs to its own day's end", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      mockAuditService.timestampFrom.set(new Date(2026, 8, 24, 8, 30, 0, 0).toISOString());
      component.onRangePickerOpened();
      expect(component.rangeSummary()).toEqual(["Start: 2026-09-24 08:30", "End: –"]);

      mockAuditService.rangeTimeMode.set(false);
      TestBed.tick();
      expect(component.rangeSummary()).toEqual(["Start: –", "End: –"]);
      component.onRangeStartDateChange(new Date(2026, 8, 28));
      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(new Date(2026, 8, 28, 0, 0, 0, 0).toISOString());
      expect(mockAuditService.timestampTo()).toBe(new Date(2026, 8, 28, 23, 59, 59, 0).toISOString());
    });

    it("Escape in the calendar after a start time (null selection) closes the picker instead of opening a new start clock", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));
      component.onClockTimeSelected({ hour: 14, minute: 30 });

      // The month view aborts a range in progress on Escape by reporting a null selection.
      strategy.selectionFinished(
        null as unknown as Date,
        new DateRange<Date>(new Date(2026, 8, 24), null),
        new KeyboardEvent("keydown")
      );

      expect(component.clockTarget()).toBeNull();
      component.onRangePickerClosed();
      expect(mockAuditService.timestampFrom()).toBe(new Date(2026, 8, 24, 14, 30, 0, 0).toISOString());
      expect(mockAuditService.timestampTo()).toBe(new Date(2026, 8, 24, 23, 59, 59, 0).toISOString());
    });

    it("Escape in the calendar before a start time (null selection) opens no clock and applies the day as a whole day", () => {
      mockAuditService.rangeTimeMode.set(true);
      component.onRangePickerOpened();
      clickDay(new Date(2026, 8, 24));
      component.onClockTimeSelected({ hour: 14, minute: 30 });
      clickDay(new Date(2026, 8, 20)); // starts over, no time picked yet

      strategy.selectionFinished(null as unknown as Date, new DateRange<Date>(null, null), new KeyboardEvent("keydown"));
      expect(component.clockTarget()).toBeNull();
      component.onRangePickerClosed();

      expect(mockAuditService.timestampFrom()).toBe(startOfLocalDayIso(new Date(2026, 8, 20)));
    });

    it("the clock opens directly below the picker panel, beside it at the clicked row only when there is no room", () => {
      const positions = clockPopupPositions(12);
      expect(positions[0]).toEqual(
        expect.objectContaining({ originX: "center", overlayX: "center", originY: "bottom", overlayY: "top" })
      );
      expect(positions[1]).toEqual(
        expect.objectContaining({ originX: "end", overlayX: "start", originY: "center", overlayY: "center", offsetY: 12 })
      );
      expect(positions[2]).toEqual(
        expect.objectContaining({ originX: "start", overlayX: "end", originY: "center", overlayY: "center", offsetY: 12 })
      );
      expect(positions.length).toBeGreaterThan(3);
    });

    it("time mode disables dragging the range, the days come from clicks only", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      const range = new DateRange<Date>(new Date(2026, 8, 24), new Date(2026, 8, 26));

      expect(strategy.createDrag(new Date(2026, 8, 24), range, new Date(2026, 8, 23))).toBeNull();
    });

    it("switching time mode off drops a half-picked time selection", () => {
      mockAuditService.rangeTimeMode.set(true);
      TestBed.tick();
      clickDay(new Date(2026, 8, 24));
      component.onClockTimeSelected({ hour: 8, minute: 30 });

      mockAuditService.rangeTimeMode.set(false);
      TestBed.tick();
      component.onRangePickerClosed();

      expect(component.clockTarget()).toBeNull();
      expect(mockAuditService.timestampFrom()).toBeNull();
    });
  });
  describe("page‑related derived signals", () => {
    it.each`
      count | expectedOptions
      ${12} | ${[5, 10, 25, 50]}
      ${10} | ${[5, 10, 25, 50]}
      ${60} | ${[5, 10, 25, 50]}
    `("total=$count → pageSizeOptions=$expectedOptions", ({ count, expectedOptions }) => {
      mockAuditService.auditResource.value.set({
        detail: undefined,
        id: 0,
        jsonrpc: "",
        signature: "",
        time: 0,
        version: "",
        versionnumber: "",
        result: {
          value: {
            count,
            auditdata: [],
            auditcolumns: [],
            current: 0
          },
          status: true
        }
      });
      expect(component.totalLength()).toBe(count);
      expect(component.pageSizeOptions()).toEqual(expectedOptions);
    });
  });

  it("pageSizeOptions should add custom page size if not included in default options", () => {
    const defaultOptions = [5, 10, 25, 50];
    mockTableUtilsService.pageSizeOptions.set(defaultOptions);
    expect(component.pageSizeOptions()).toEqual(defaultOptions);

    // Check custom page size is added but does not mutate the options from the service
    const customOptions = [5, 10, 15, 25, 50];
    mockAuditService.pageSize.set(15);
    expect(component.pageSizeOptions()).toEqual(customOptions);
    expect(mockTableUtilsService.pageSizeOptions()).toEqual(defaultOptions);

    // custom page size should still be included if selected pageSize changes
    mockAuditService.pageSize.set(10);
    expect(component.pageSizeOptions()).toEqual(customOptions);
  });

  it("auditDataSource updates when auditResource changes", () => {
    const rows: AuditData[] = [{ user: "alice" } as AuditData];
    mockAuditService.auditResource.value.set({
      detail: undefined,
      id: 0,
      jsonrpc: "",
      signature: "",
      time: 0,
      version: "",
      versionnumber: "",
      result: {
        value: {
          count: 1,
          auditdata: rows,
          auditcolumns: [],
          current: 0
        },
        status: true
      }
    });
    expect(component.auditDataSource() instanceof MatTableDataSource).toBe(true);
    expect(component.auditDataSource().data).toEqual(rows);
  });

  it("onPageEvent stores the 0-based paginator index as the 1-based API page", () => {
    component.onPageEvent({
      pageSize: 15,
      pageIndex: 2,
      length: 0,
      previousPageIndex: 1
    });
    expect(mockAuditService.pageSize()).toBe(15);
    expect(mockAuditService.pageIndex()).toBe(3);
  });
});

describe("AuditComponent (template rendering)", () => {
  let fixture: ComponentFixture<AuditComponent>;
  let component: AuditComponent;
  let mockAuditService: MockAuditService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [AuditComponent],
      providers: [
        provideHttpClient(),
        { provide: ActivatedRoute, useValue: { params: of({ id: "123" }) } },
        { provide: MockAuditService, useClass: MockAuditService },
        { provide: MockTableUtilsService, useClass: MockTableUtilsService },
        { provide: MockContentService, useClass: MockContentService },
        { provide: MockAuthService, useClass: MockAuthService },
        { provide: AuditService, useExisting: MockAuditService },
        { provide: TableUtilsService, useExisting: MockTableUtilsService },
        { provide: ContentService, useExisting: MockContentService },
        { provide: AuthService, useExisting: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    const authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["auditlog"] });

    fixture = TestBed.createComponent(AuditComponent);
    component = fixture.componentInstance;
    mockAuditService = TestBed.inject(MockAuditService);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  const showRows = (rows: AuditData[], count = 1) =>
    mockAuditService.auditResource.value.set({
      detail: undefined,
      id: 0,
      jsonrpc: "",
      signature: "",
      time: 0,
      version: "",
      versionnumber: "",
      result: {
        value: {
          count,
          auditdata: rows,
          auditcolumns: [],
          current: 0
        },
        status: true
      }
    });

  it.each([AuditComponent, AuditSelfServiceComponent])(
    "%p shows the 1-based API page on the 0-based paginator",
    (componentType) => {
      const pageFixture = TestBed.createComponent(componentType);
      showRows(
        Array.from({ length: 10 }, () => ({}) as AuditData),
        25
      );
      mockAuditService.pageIndex.set(2);
      pageFixture.detectChanges();

      const paginator = pageFixture.debugElement.query(By.directive(MatPaginator)).componentInstance as MatPaginator;
      expect(paginator.pageIndex).toBe(1);
    }
  );

  it("renders the startdate column as one ISO date and time, not the raw server string", () => {
    showRows([{ startdate: "2026-01-15T10:00:00.123456" } as AuditData]);
    fixture.detectChanges();

    const startdateColumnIndex = component.columnKeysMap.findIndex((c) => c.key === "startdate");
    const cells = fixture.nativeElement.querySelectorAll("tbody td");
    const cellText = cells[startdateColumnIndex].textContent.trim();

    expect(cellText).toContain("2026-01-15 10:00:00");
    expect(cellText).not.toContain("2026-01-15T10:00:00");
  });

  describe("range picker in the browser DOM", () => {
    const cells = () => Array.from(document.querySelectorAll<HTMLElement>(".mat-calendar-body-cell"));
    const dial = () => document.querySelector<HTMLElement>(".cdk-overlay-container app-clock-dial");
    // The day the tenth calendar cell stands for: the picker opens on the current month without a range.
    const tenth = () => {
      const today = new Date();
      return new Date(today.getFullYear(), today.getMonth(), 10);
    };
    // Picks a value on the open clock by tapping it at a clock angle and radius (in the dial's 256px box).
    const tapDial = (degrees: number, radius: number) => {
      const face = dial()!.querySelector<HTMLElement>("[role=slider]")!;
      jest.spyOn(face, "getBoundingClientRect").mockReturnValue({
        left: 0,
        top: 0,
        width: 256,
        height: 256,
        right: 256,
        bottom: 256,
        x: 0,
        y: 0,
        toJSON: () => ({})
      });
      const rad = (degrees * Math.PI) / 180;
      const init = { clientX: 128 + radius * Math.sin(rad), clientY: 128 - radius * Math.cos(rad), bubbles: true };
      // jsdom has no PointerEvent: a MouseEvent of the pointer type carries the coordinates the dial reads.
      face.dispatchEvent(new MouseEvent("pointerdown", init));
      face.dispatchEvent(new MouseEvent("pointerup", init));
      fixture.detectChanges();
    };
    const markClasses = (text: string) =>
      Array.from(dial()!.querySelectorAll(".clock-dial__mark")).find((mark) => mark.textContent?.trim() === text)
        ?.classList;

    beforeEach(() => {
      mockAuditService.auditResource.value.set({
        detail: undefined,
        id: 0,
        jsonrpc: "",
        signature: "",
        time: 0,
        version: "",
        versionnumber: "",
        result: {
          value: { count: 1, auditdata: [{ startdate: "2026-01-15T10:00:00" } as AuditData], auditcolumns: [], current: 0 },
          status: true
        }
      });
      fixture.detectChanges();
    });

    afterEach(() => component.rangePicker()?.close());

    it("time mode shows both summary lines before any day is picked", () => {
      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      component.rangePicker()!.open();
      fixture.detectChanges();

      const lines = Array.from(document.querySelectorAll(".audit-range-time-summary > div")).map((line) =>
        line.textContent?.trim()
      );
      expect(lines).toEqual(["Start: –", "End: –"]);
    });

    it("time mode announces the summary and the hint as one polite live region", () => {
      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      component.rangePicker()!.open();
      fixture.detectChanges();

      const live = document.querySelector(".audit-range-time-live");
      expect(live?.getAttribute("aria-live")).toBe("polite");
      expect(live?.getAttribute("aria-atomic")).toBe("true");
      expect(live?.querySelector(".audit-range-time-summary")).not.toBeNull();
      expect(live?.querySelector(".audit-range-time-hint")?.textContent?.trim()).toBe("Pick the start day");
    });

    it("checkbox off renders no summary block and no actions row", () => {
      component.rangePicker()!.open();
      fixture.detectChanges();

      expect(document.querySelector(".mat-datepicker-content")).not.toBeNull();
      expect(document.querySelector(".audit-range-time-summary")).toBeNull();
      expect(document.querySelector(".mat-datepicker-actions")).toBeNull();
    });

    it("checkbox off: two day clicks apply whole days and close the picker, no clock appears", () => {
      const picker = component.rangePicker()!;
      const closeSpy = jest.spyOn(picker, "close");
      picker.open();
      fixture.detectChanges();

      cells()[9].click();
      fixture.detectChanges();
      expect(dial()).toBeNull();
      cells()[11].click();
      fixture.detectChanges();

      const first = tenth();
      const last = new Date(first.getFullYear(), first.getMonth(), 12);
      expect(mockAuditService.timestampFrom()).toBe(new Date(first.setHours(0, 0, 0, 0)).toISOString());
      expect(mockAuditService.timestampTo()).toBe(new Date(last.setHours(23, 59, 59, 0)).toISOString());
      expect(closeSpy).toHaveBeenCalled();
      expect(dial()).toBeNull();
    });

    it("time mode: start clock at the clicked day, same day again gives the end clock without earlier times", () => {
      const picker = component.rangePicker()!;
      picker.open();
      fixture.detectChanges();
      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      const closeSpy = jest.spyOn(picker, "close");
      const summary = () => document.querySelector(".audit-range-time-summary")?.textContent ?? "";
      const day = tenth();
      const dayText = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-10`;
      // Nothing picked yet: both lines show their placeholder and the hint asks for the start day.
      const hint = () => document.querySelector(".audit-range-time-hint")?.textContent?.trim();
      expect(hint()).toBe("Pick the start day");
      expect(summary()).toContain("Start: –");
      expect(summary()).toContain("End: –");

      cells()[9].click();
      fixture.detectChanges();
      expect(dial()).not.toBeNull();
      expect(dial()!.textContent).toContain("Start time");
      expect(dial()!.closest(".cdk-overlay-pane")).not.toBeNull();

      tapDial(240, 104); // 8 on the outer ring
      tapDial(180, 104); // minute 30
      expect(dial()).toBeNull();
      expect(picker.opened).toBe(true);
      expect(closeSpy).not.toHaveBeenCalled();
      expect(mockAuditService.timestampFrom()).toBeNull();
      // The hint now offers the end day, or closing the picker for this day.
      expect(hint()).toBe("Pick the end day, or close to filter this day");
      expect(summary()).toContain(`Start: ${dayText} 08:30`);
      expect(summary()).toContain("End: –");

      cells()[9].click();
      fixture.detectChanges();
      expect(picker.opened).toBe(true);
      expect(dial()!.textContent).toContain("End time");
      expect(markClasses("7")?.contains("clock-dial__mark--disabled")).toBe(true);
      expect(markClasses("8")?.contains("clock-dial__mark--disabled")).toBe(false);
      expect(markClasses("17")?.contains("clock-dial__mark--disabled")).toBe(false);

      tapDial(210, 104); // 7 is disabled, nothing happens
      const slider = dial()!.querySelector("[role=slider]")!;
      expect(document.getElementById(slider.getAttribute("aria-labelledby")!)?.textContent?.trim()).toBe("Hour");
      tapDial(150, 68); // 17 on the inner ring
      tapDial(90, 104); // minute 15
      fixture.detectChanges();
      expect(summary()).toContain(`End: ${dayText} 17:15`);
      expect(mockAuditService.timestampFrom()).toBe(
        new Date(day.getFullYear(), day.getMonth(), 10, 8, 30, 0, 0).toISOString()
      );
      expect(mockAuditService.timestampTo()).toBe(
        new Date(day.getFullYear(), day.getMonth(), 10, 17, 15, 0, 0).toISOString()
      );
      expect(closeSpy).toHaveBeenCalled();
      expect(dial()).toBeNull();
    });

    it("time mode: the clock is positioned against the picker panel, not the clicked cell", () => {
      const picker = component.rangePicker()!;
      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      picker.open();
      fixture.detectChanges();

      const { origin, positions } = component.clockPopupPositioning(cells()[9]);

      expect(origin).toBe(cells()[9].closest(".mat-datepicker-content"));
      expect(positions[0].originY).toBe("bottom");
      expect(positions[0].overlayY).toBe("top");
    });

    it("time mode: the open clock has the focus in its hour field, and closing it gives the focus back to the day", () => {
      const picker = component.rangePicker()!;
      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      picker.open();
      fixture.detectChanges();
      cells()[9].focus();
      cells()[9].click();
      fixture.detectChanges();

      expect(document.activeElement).toBe(dial()!.querySelector(".clock-dial__field--hour"));

      document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true }));
      fixture.detectChanges();

      expect(dial()).toBeNull();
      expect(document.activeElement).toBe(cells()[9]);
    });

    // Escape after a start time is picked closes the picker and applies that day from the start time (rule 1), whatever
    // has the focus: the month view swallows Escape while its range preview is shown (hover, or focus on a day cell,
    // which the clock gives back to the clicked cell), otherwise the picker overlay gets it.
    it.each`
      situation                                    | escape
      ${"hover preview on a later day"}            | ${"hover"}
      ${"focus back on the clicked cell"}          | ${"cell"}
      ${"focus outside the calendar"}              | ${"body"}
    `("time mode: Escape after a start time with $situation closes the picker and applies rule 1", async ({ escape }) => {
      const picker = component.rangePicker()!;
      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      picker.open();
      fixture.detectChanges();
      cells()[9].click();
      fixture.detectChanges();
      tapDial(240, 104); // 8
      tapDial(180, 104); // 30
      expect(dial()).toBeNull();

      const esc = () => new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true });
      if (escape === "hover") {
        cells()[12].dispatchEvent(new MouseEvent("mouseenter"));
        fixture.detectChanges();
        cells()[9].dispatchEvent(esc());
      } else if (escape === "cell") {
        expect(document.activeElement).toBe(cells()[9]);
        document.activeElement!.dispatchEvent(esc());
      } else {
        (document.activeElement as HTMLElement | null)?.blur();
        document.body.dispatchEvent(esc());
      }
      fixture.detectChanges();
      await new Promise((resolve) => setTimeout(resolve));
      fixture.detectChanges();

      expect(dial()).toBeNull();
      expect(picker.opened).toBe(false);
      const day = tenth();
      expect(mockAuditService.timestampFrom()).toBe(
        new Date(day.getFullYear(), day.getMonth(), 10, 8, 30, 0, 0).toISOString()
      );
      expect(mockAuditService.timestampTo()).toBe(
        new Date(day.getFullYear(), day.getMonth(), 10, 23, 59, 59, 0).toISOString()
      );
    });

    it("time mode: Escape closes only the clock, the picker stays open", () => {
      const picker = component.rangePicker()!;
      mockAuditService.rangeTimeMode.set(true);
      fixture.detectChanges();
      picker.open();
      fixture.detectChanges();
      cells()[9].click();
      fixture.detectChanges();
      expect(dial()).not.toBeNull();

      document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, bubbles: true }));
      fixture.detectChanges();

      expect(dial()).toBeNull();
      expect(picker.opened).toBe(true);
    });
  });

  it("opens the range picker instead of inserting a keyword when the date header filter button is clicked", () => {
    mockAuditService.auditResource.value.set({
      detail: undefined,
      id: 0,
      jsonrpc: "",
      signature: "",
      time: 0,
      version: "",
      versionnumber: "",
      result: {
        value: {
          count: 1,
          auditdata: [{ startdate: "2026-01-15T10:00:00" } as AuditData],
          auditcolumns: [],
          current: 0
        },
        status: true
      }
    });
    fixture.detectChanges();
    const openSpy = jest.spyOn(component.rangePicker()!, "open");
    const toggleSpy = jest.spyOn(component, "toggleFilter");
    const idx = component.columnKeysMap.findIndex((c) => c.key === "startdate");
    const headerCells = fixture.nativeElement.querySelectorAll("th");
    const headerButton: HTMLButtonElement = headerCells[idx].querySelector(".filter-button");

    headerButton.click();

    expect(openSpy).toHaveBeenCalled();
    expect(toggleSpy).not.toHaveBeenCalled();
  });

  it.each([
    ["admin", AuditComponent],
    ["self-service", AuditSelfServiceComponent]
  ])("names the %s filter input by its visible label", (_, componentType) => {
    showRows([{ startdate: "2026-01-15T10:00:00.123456" } as AuditData]);
    const filterFixture = TestBed.createComponent<AuditComponent>(componentType);
    filterFixture.detectChanges();
    const element: HTMLElement = filterFixture.nativeElement;
    const input = element.querySelector<HTMLInputElement>(".mat-mdc-form-field input")!;

    expect(input.hasAttribute("aria-label")).toBe(false);
    expect(element.querySelector(`label[for="${input.id}"]`)?.textContent).toContain("Filter Audit Log");
  });

  describe("typed time interval in the filter field", () => {
    const timeKeys = [
      ["admin", "date", AuditComponent],
      ["admin", "startdate", AuditComponent],
      ["self-service", "date", AuditSelfServiceComponent],
      ["self-service", "startdate", AuditSelfServiceComponent]
    ] as const;

    // Renders the component with the filter field and returns the field and a way to type into it.
    const renderFilterField = (componentType: typeof AuditComponent) => {
      showRows([{ startdate: "2026-01-15T10:00:00.123456" } as AuditData]);
      const filterFixture = TestBed.createComponent<AuditComponent>(componentType);
      filterFixture.detectChanges();
      const input = filterFixture.nativeElement.querySelector(".mat-mdc-form-field input") as HTMLInputElement;
      const type = (text: string): void => {
        input.value = text;
        input.dispatchEvent(new Event("input"));
        filterFixture.detectChanges();
      };
      const pressEnter = (): void => {
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter" }));
        filterFixture.detectChanges();
      };
      const hint = (): HTMLElement | null =>
        Array.from((filterFixture.nativeElement as HTMLElement).querySelectorAll<HTMLElement>("mat-hint")).find((h) =>
          h.textContent?.includes("Press enter to apply the filter")
        ) ?? null;
      return { input, type, pressEnter, hint };
    };

    it.each(timeKeys)("%s: a typed %s interval is applied on Enter only", (_, key, componentType) => {
      const { type, pressEnter } = renderFilterField(componentType);
      const applied = mockAuditService.activeFilter();

      type(`${key}: foo/bar`);

      expect(mockAuditService.handleFilterInput).not.toHaveBeenCalled();
      expect(mockAuditService.activeFilter()).toBe(applied);

      pressEnter();

      expect(mockAuditService.applyFilterInput).toHaveBeenCalledTimes(1);
      const event = mockAuditService.applyFilterInput.mock.calls[0][0] as Event;
      expect((event.target as HTMLInputElement).value).toBe(`${key}: foo/bar`);
    });

    it.each(timeKeys)("%s: typing next to an unchanged applied %s interval still applies live", (_, key, componentType) => {
      mockAuditService.activeFilter.set(new FilterValue({ value: `${key}: 2026-11-05/2026-11-06` }));
      const { type } = renderFilterField(componentType);

      type(`user: x ${key}: 2026-11-05/2026-11-06`);

      expect(mockAuditService.handleFilterInput).toHaveBeenCalledTimes(1);
    });

    it.each(timeKeys)("%s: shows the press enter hint for a typed %s interval", (_, key, componentType) => {
      const { type, pressEnter, hint } = renderFilterField(componentType);

      type(`${key}: foo/bar`);
      expect(hint()).not.toBeNull();

      pressEnter();
      expect(hint()).toBeNull();
    });

    it.each(["admin", "self-service"] as const)("%s: shows no press enter hint for a plain text filter", (kind) => {
      const { type, hint } = renderFilterField(kind === "admin" ? AuditComponent : AuditSelfServiceComponent);

      type("user: x");

      expect(hint()).toBeNull();
    });
  });

  describe("links", () => {
    const hrefOf =(element: HTMLElement, text: string) =>
      Array.from(element.querySelectorAll<HTMLAnchorElement>("tbody a"))
        .find((a) => a.textContent?.trim() === text)
        ?.getAttribute("href");

    beforeEach(() => showRows([{ serial: "S-1", container_serial: "C-1", user: "alice", realm: "r1" } as AuditData]));

    it.each([
      ["admin", AuditComponent],
      ["self-service", AuditSelfServiceComponent]
    ])("links the %s token and container serials to their details pages", (_, componentType) => {
      const linkFixture = TestBed.createComponent<AuditComponent>(componentType);
      linkFixture.detectChanges();

      expect(hrefOf(linkFixture.nativeElement, "S-1")).toBe("/tokens/details/S-1");
      expect(hrefOf(linkFixture.nativeElement, "C-1")).toBe("/containers/details/C-1");
    });

    it.each([
      ["admin", AuditComponent],
      ["self-service", AuditSelfServiceComponent]
    ])("passes the %s axe accessibility checks", async (_, componentType) => {
      const axeFixture = TestBed.createComponent<AuditComponent>(componentType);
      axeFixture.detectChanges();

      expect(await axe(axeFixture.nativeElement)).toHaveNoViolations();
    });

    it("links admins to the details of the user in their realm", () => {
      fixture.detectChanges();

      expect(hrefOf(fixture.nativeElement, "alice")).toBe("/users/details/alice?realm=r1");
    });

    it("links users to their own details", () => {
      const selfFixture = TestBed.createComponent(AuditSelfServiceComponent);
      selfFixture.detectChanges();

      expect(hrefOf(selfFixture.nativeElement, "alice")).toBe("/users/details");
    });
  });
});
