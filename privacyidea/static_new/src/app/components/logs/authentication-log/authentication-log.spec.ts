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
import { provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PageEvent } from "@angular/material/paginator";
import { AuthenticationLogService } from "@services/authentication-log/authentication-log.service";
import { AuthService } from "@services/auth/auth.service";
import { ClientsService } from "@services/clients/clients.service";
import { ContentService } from "@services/content/content.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  MockAuthenticationLogService,
  MockClientsService,
  MockContentService,
  MockPiResponse,
  MockRealmService,
  MockTableUtilsService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";

import { AuthenticationLog } from "./authentication-log";

describe("AuthenticationLog", () => {
  let component: AuthenticationLog;
  let fixture: ComponentFixture<AuthenticationLog>;
  let service: MockAuthenticationLogService;
  let tableUtils: MockTableUtilsService;
  let clientsService: MockClientsService;
  let authService: MockAuthService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [AuthenticationLog],
      providers: [
        provideHttpClient(),
        { provide: MockAuthenticationLogService, useClass: MockAuthenticationLogService },
        { provide: MockTableUtilsService, useClass: MockTableUtilsService },
        { provide: MockContentService, useClass: MockContentService },
        { provide: MockRealmService, useClass: MockRealmService },
        { provide: MockClientsService, useClass: MockClientsService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: AuthenticationLogService, useExisting: MockAuthenticationLogService },
        { provide: TableUtilsService, useExisting: MockTableUtilsService },
        { provide: ContentService, useExisting: MockContentService },
        { provide: RealmService, useExisting: MockRealmService },
        { provide: ClientsService, useExisting: MockClientsService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AuthenticationLog);
    component = fixture.componentInstance;
    service = TestBed.inject(MockAuthenticationLogService);
    tableUtils = TestBed.inject(MockTableUtilsService);
    clientsService = TestBed.inject(MockClientsService);
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    fixture.detectChanges();
  });

  it("creates and exposes one column key per column definition", () => {
    expect(component).toBeTruthy();
    expect(component.visibleColumnKeys().length).toBe(component.columnKeysMap.length);
  });

  it("hides the user-identifying columns in self-service", () => {
    authService.role.set("user");
    const keys = component.visibleColumnKeys();
    expect(keys).not.toContain("username");
    expect(keys).not.toContain("realm");
    expect(keys).not.toContain("resolver");
    expect(keys).not.toContain("uid");
    // Non-user columns stay visible.
    expect(keys).toContain("timestamp");
    expect(keys).toContain("event_type");
    expect(keys).toContain("source_ip");
  });

  it("renders one row per returned entry", () => {
    service.authenticationLogResource.set(
      MockPiResponse.fromValue({
        auth_logs: [{ id: 1, event_type: "LOGIN_SUCCESS", timestamp: "2026-06-22T10:00:00+00:00" }],
        count: 1,
        current: 1,
        prev: null,
        next: null
      })
    );
    fixture.detectChanges();
    const rows = fixture.nativeElement.querySelectorAll("tr[mat-row]");
    expect(rows.length).toBe(1);
    expect(component.totalLength()).toBe(1);
  });

  it("onPageEvent forwards page size and converts the 0-based event index to the 1-based service page", () => {
    component.onPageEvent({ pageIndex: 3, pageSize: 50 } as PageEvent);
    expect(service.pageSize()).toBe(50);
    expect(service.pageIndex()).toBe(4);
  });

  it("onKeywordClick toggles the keyword in the filter for free-text columns", () => {
    tableUtils.toggleKeywordInFilter.mockReturnValue(new FilterValue({ value: "client_label: " }));
    component.onKeywordClick("client_label");
    expect(tableUtils.toggleKeywordInFilter).toHaveBeenCalledWith(expect.objectContaining({ keyword: "client_label" }));
    expect(service.authenticationLogFilter().hasKey("client_label")).toBe(true);
  });

  it("onSortClick delegates to tableUtilsService with the timestamp fallback", () => {
    component.onSortClick("event_type");
    expect(tableUtils.onSortButtonClick).toHaveBeenCalledWith("event_type", service.sort, {
      active: "timestamp",
      direction: ""
    });
  });

  it("getFilterIconName reflects whether the keyword is active", () => {
    expect(component.getFilterIconName("serial")).toBe("filter_alt");
    service.authenticationLogFilter.set(new FilterValue({ value: "serial: PISP0001" }));
    expect(component.getFilterIconName("serial")).toBe("filter_alt_off");
  });

  it("classifies event types by outcome severity, not by name suffix", () => {
    expect(component.getEventTypeClass("LOGIN_SUCCESS")).toBe("highlight-true");
    expect(component.getEventTypeClass("PASSWORD_FAIL")).toBe("highlight-false");
    expect(component.getEventTypeClass("CHALLENGE_TRIGGERED")).toBe("highlight-warning");
    // Failures that do not end in *_FAIL must still read as failures.
    expect(component.getEventTypeClass("NO_TOKEN")).toBe("highlight-false");
    expect(component.getEventTypeClass("NO_USABLE_TOKEN")).toBe("highlight-false");
    expect(component.getEventTypeClass("USER_UNKNOWN")).toBe("highlight-false");
    expect(component.getEventTypeClass("NOT_AUTHORIZED")).toBe("highlight-false");
    expect(component.getEventTypeClass("UNKNOWN_FAIL_REASON")).toBe("highlight-false");
    // Unknown/empty values stay unstyled.
    expect(component.getEventTypeClass("")).toBe("");
    expect(component.getEventTypeClass("SOMETHING_NEW")).toBe("");
  });

  it("exposes the three user-role filter options", () => {
    expect(component.userRoleOptions).toEqual([
      { label: "User", value: "user" },
      { label: "Internal Admin", value: "admin-internal" },
      { label: "External Admin", value: "admin-external" }
    ]);
  });

  it("shows the More Filter button for an admin and hides it in self-service", () => {
    expect(fixture.nativeElement.querySelector('button[aria-label="More Filter"]')).not.toBeNull();
    authService.role.set("user");
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('button[aria-label="More Filter"]')).toBeNull();
  });

  it("userRoleBadge flags only admins; regular users and unknown values get no badge", () => {
    expect(component.userRoleBadge("admin-internal")).toEqual(
      expect.objectContaining({ label: "internal admin", class: "role-badge-admin-internal" })
    );
    expect(component.userRoleBadge("admin-external")).toEqual(
      expect.objectContaining({ label: "external admin", class: "role-badge-admin-external" })
    );
    expect(component.userRoleBadge("user")).toBeNull();
    expect(component.userRoleBadge(null)).toBeNull();
    expect(component.userRoleBadge(undefined)).toBeNull();
    expect(component.userRoleBadge("")).toBeNull();
  });

  it("renders an admin role badge behind the username but none for a regular user", () => {
    service.authenticationLogResource.set(
      MockPiResponse.fromValue({
        auth_logs: [
          {
            id: 1,
            event_type: "LOGIN_SUCCESS",
            timestamp: "2026-06-22T10:00:00+00:00",
            username: "alice",
            user_role: "user"
          },
          {
            id: 2,
            event_type: "LOGIN_SUCCESS",
            timestamp: "2026-06-22T10:01:00+00:00",
            username: "bob",
            user_role: "admin-internal"
          }
        ],
        count: 2,
        current: 1,
        prev: null,
        next: null
      })
    );
    fixture.detectChanges();
    const badges = fixture.nativeElement.querySelectorAll(".role-badge");
    expect(badges.length).toBe(1);
    expect(badges[0].textContent.trim()).toBe("internal admin");
    expect(badges[0].classList).toContain("role-badge-admin-internal");
  });

  it("formatInfo serializes other_info and tolerates null", () => {
    expect(component.formatInfo({ a: 1 })).toBe('{"a":1}');
    expect(component.formatInfo(null)).toBe("");
  });

  it("infoEntries renders key/value rows, CSV arrays, a sub-list for nested dicts and JSON for deeper nesting", () => {
    expect(component.infoEntries(null)).toEqual([]);
    expect(
      component.infoEntries({
        serial: "TOTP001",
        roles: ["admin", "user"],
        truncated: { username: "abc", deep: { x: 1 } },
        n: 3
      })
    ).toEqual([
      { key: "serial", value: "TOTP001" },
      { key: "roles", value: "admin, user" },
      {
        key: "truncated",
        children: [
          { key: "username", value: "abc" },
          { key: "deep", value: '{"x":1}' }
        ]
      },
      { key: "n", value: "3" }
    ]);
  });

  it("editing start_time/end_time in the filter text drives the time filter", () => {
    // A valid edit parses into the timestamp signal (explicit offset -> timezone-independent).
    service.authenticationLogFilter.set(new FilterValue().addEntry("start_time", "2026-06-02 10:00:00 +00:00"));
    fixture.detectChanges();
    expect(service.timestampFrom()).toBe("2026-06-02T10:00:00.000Z");

    // Removing the entry clears its bound.
    service.authenticationLogFilter.set(new FilterValue());
    fixture.detectChanges();
    expect(service.timestampFrom()).toBeNull();

    // An unparseable (in-progress) edit is ignored rather than clearing an active filter.
    service.timestampTo.set("2026-06-02T12:00:00.000Z");
    service.authenticationLogFilter.set(new FilterValue().addEntry("end_time", "2026-99-99 99:99:99 +00:00"));
    fixture.detectChanges();
    expect(service.timestampTo()).toBe("2026-06-02T12:00:00.000Z");
  });

  it("floors the leftmost slider position to the oldest entry's second (so a sub-second entry is not excluded)", () => {
    // A sub-second oldest timestamp: the start must floor to its whole second so the entry stays >= start_time.
    service.oldestTimestamp.set("2020-01-01T00:00:00.123456Z");
    fixture.detectChanges();
    // Drag start fully left, end fully right, then commit: start floors to the second, end is open ("now").
    component.rangeStart.set(0);
    component.rangeEnd.set(component.rangeSliderSteps);
    component.commitTimeRange();
    expect(service.timestampFrom()).toBe("2020-01-01T00:00:00.000Z");
    expect(service.timestampTo()).toBeNull();
  });

  it("setFilterValues stores a multi-value selection as CSV", () => {
    component.setFilterValues("event_type", ["LOGIN_SUCCESS", "MFA_FAIL"]);
    expect(service.authenticationLogFilter().getValueOfKey("event_type")).toBe("LOGIN_SUCCESS,MFA_FAIL");
  });

  it("addFilterValue appends a value to the column filter and ignores duplicates", () => {
    component.addFilterValue("username", "alice");
    expect(service.authenticationLogFilter().getValueOfKey("username")).toBe("alice");

    component.addFilterValue("username", "bob");
    expect(service.authenticationLogFilter().getValueOfKey("username")).toBe("alice,bob");

    component.addFilterValue("username", "alice");
    expect(service.authenticationLogFilter().getValueOfKey("username")).toBe("alice,bob");
  });

  it("setFilterValues removes the key when empty", () => {
    component.setFilterValues("event_type", []);
    expect(service.authenticationLogFilter().hasKey("event_type")).toBe(false);
  });

  it("selectedFilterValues reads the current CSV selection back as an array", () => {
    component.setFilterValues("realm", ["realm1", "realm2"]);
    expect(component.selectedFilterValues("realm")).toEqual(["realm1", "realm2"]);
    expect(component.selectedFilterValues("event_type")).toEqual([]);
  });

  it("derives event-type filter options from the service event types (not a hardcoded list)", () => {
    // Options mirror the backend-provided event types exposed by the service.
    expect(component.eventTypeOptions()).toEqual(service.eventTypes().map((entry) => entry.name));
    expect(component.eventTypeOptions()).toContain("LOGIN_SUCCESS");

    // Reflects updates to the service list.
    service.eventTypes.set([{ name: "ONLY_ONE", outcome: "success" }]);
    expect(component.eventTypeOptions()).toEqual(["ONLY_ONE"]);
  });

  it("exposes client-label options mapping friendly name -> identifier", () => {
    expect(component.clientLabelOptions).toContainEqual({ label: "Keycloak", value: "privacyIDEA-Keycloak" });
    expect(component.clientLabelOptions.every((o) => o.label && o.value)).toBe(true);
  });

  it("requests known clients on init for the source-IP options", () => {
    expect(clientsService.requestClientsForAutocomplete).toHaveBeenCalled();
  });

  it("derives unique sorted source-IP options from known clients; menu hidden when none", () => {
    expect(component.sourceIpOptions()).toEqual([]);
    expect(component.showSourceIpMenu()).toBe(false);

    clientsService.setClients({
      pam: [{ ip: "10.0.0.2" }, { ip: "10.0.0.1" }],
      keycloak: [{ ip: "10.0.0.1" }, { ip: null }]
    });

    expect(component.sourceIpOptions()).toEqual(["10.0.0.1", "10.0.0.2"]);
    expect(component.showSourceIpMenu()).toBe(true);
  });

  it("onAddCustomFilter adds the key to the main filter and focuses the input for free-text entry", () => {
    jest.useFakeTimers();
    const focusSpy = jest.spyOn(component.filterInput.nativeElement, "focus");

    component.onAddCustomFilter("client_label");
    expect(service.authenticationLogFilter().hasKey("client_label")).toBe(true);
    // No value yet -> nothing selected; the user types the value in the main input.
    expect(component.selectedFilterValues("client_label")).toEqual([]);

    // Focus is deferred (the closing menu restores focus to its trigger first).
    jest.runAllTimers();
    expect(focusSpy).toHaveBeenCalled();
    jest.useRealTimers();
  });

  describe("time filter", () => {
    it("selectTimePreset sets from to a past ISO string, clears to and selectedPreset switches", () => {
      const before = Date.now();
      component.selectTimePreset("1h");
      const after = Date.now();

      const from = service.timestampFrom();
      expect(from).not.toBeNull();
      const fromMs = new Date(from!).getTime();
      // Should be ~1 hour before now (within a 1-second tolerance either side).
      expect(fromMs).toBeGreaterThanOrEqual(before - 3_600_000 - 1000);
      expect(fromMs).toBeLessThanOrEqual(after - 3_600_000 + 1000);
      expect(service.timestampTo()).toBeNull();
      expect(component.selectedPreset()).toBe("1h");
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(true);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(false);
      // Filter display value includes local UTC offset (e.g. +00:00, +02:00).
      expect(service.authenticationLogFilter().getValueOfKey("start_time")).toMatch(/( [+-]\d{2}:\d{2}| Z)$/);
    });

    it("selectTimePreset('3m') subtracts 3 calendar months", () => {
      const before = new Date();
      component.selectTimePreset("3m");
      const after = new Date();

      const from = new Date(service.timestampFrom()!);
      const expectedMin = new Date(before);
      expectedMin.setMonth(expectedMin.getMonth() - 3);
      const expectedMax = new Date(after);
      expectedMax.setMonth(expectedMax.getMonth() - 3);

      expect(from.getTime()).toBeGreaterThanOrEqual(expectedMin.getTime() - 1000);
      expect(from.getTime()).toBeLessThanOrEqual(expectedMax.getTime() + 1000);
    });

    it("clearTimeFilter resets from, to, selectedPreset and removes keys from filter text", () => {
      component.selectTimePreset("7d");
      component.clearTimeFilter();

      expect(service.timestampFrom()).toBeNull();
      expect(service.timestampTo()).toBeNull();
      expect(component.selectedPreset()).toBeNull();
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(false);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(false);
    });

    it("clearAllFilters clears both the text filter and the time filter", () => {
      // A time filter lives in its own signals; clearing the text alone used to leave it silently active.
      service.authenticationLogFilter.set(service.authenticationLogFilter().copyWith({ value: "username: alice" }));
      component.selectTimePreset("7d");
      expect(service.timestampFrom()).not.toBeNull();

      component.clearAllFilters();

      expect(service.timestampFrom()).toBeNull();
      expect(service.timestampTo()).toBeNull();
      expect(component.selectedPreset()).toBeNull();
      expect(service.authenticationLogFilter().value).toBe("");
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(false);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(false);
    });

    it("commitTimeRange applies the slider thumbs as an ordered start/end within the window", () => {
      const steps = component.rangeSliderSteps;
      // Start thumb just inside the oldest edge, end thumb just below "now".
      component.onRangeStartInput(1);
      component.onRangeEndInput(steps - 1);
      component.commitTimeRange();

      const from = new Date(service.timestampFrom()!).getTime();
      const to = new Date(service.timestampTo()!).getTime();
      expect(from).toBeLessThan(to);
      expect(component.selectedPreset()).toBeNull();
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(true);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(true);
    });

    it("commitTimeRange with the end thumb at max leaves the upper bound open (no end_time)", () => {
      component.onRangeStartInput(10);
      component.onRangeEndInput(component.rangeSliderSteps);
      component.commitTimeRange();

      expect(service.timestampFrom()).not.toBeNull();
      expect(service.timestampTo()).toBeNull();
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(true);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(false);
    });

    it("the slider window and thumbs adjust to the selected preset", () => {
      component.selectTimePreset("1h");
      // The window shrinks to ~1 hour and the thumbs span the whole window (start at 0, end at now).
      expect(component.rangeStart()).toBe(0);
      expect(component.rangeEnd()).toBe(component.rangeSliderSteps);
      expect(component.sliderWindowMs()).toBeGreaterThan(0);
      expect(component.sliderWindowMs()).toBeLessThanOrEqual(3_600_000 + 1000);

      // A wider preset yields a wider window, so short ranges get finer resolution under short presets.
      component.selectTimePreset("30d");
      expect(component.sliderWindowMs()).toBeGreaterThan(29 * 86_400_000);
    });

    it("clearTimeFilter resets the slider window to the default", () => {
      component.selectTimePreset("1h");
      expect(component.sliderWindowMs()).toBeLessThan(86_400_000);
      component.clearTimeFilter();
      expect(component.sliderWindowMs()).toBe(365 * 86_400_000);
    });
  });

  it("splitSerials splits comma-separated serials, trims, and drops blanks", () => {
    expect(component.splitSerials("PISP0001")).toEqual(["PISP0001"]);
    expect(component.splitSerials("PISP0001, PISP0002 ,PISP0003")).toEqual(["PISP0001", "PISP0002", "PISP0003"]);
    expect(component.splitSerials("PISP0001,,")).toEqual(["PISP0001"]);
    expect(component.splitSerials("")).toEqual([]);
    expect(component.splitSerials(null)).toEqual([]);
  });

  it("noDataText shows generic message when no filter is active", () => {
    service.filterParams.set({});
    expect(component.noDataText()).toContain("No authentication log entries.");
    expect(component.noDataText()).not.toContain("matching the filter");
  });

  it("noDataText shows filter-specific message when a filter is set", () => {
    service.filterParams.set({});
    expect(component.noDataText()).toContain("No authentication log entries.");
    expect(component.noDataText()).not.toContain("matching the filter");

    service.filterParams.set({ username: "alice" });
    expect(component.noDataText()).toContain("matching the filter");
  });
});
