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
import { MatTableDataSource } from "@angular/material/table";
import { provideRouter } from "@angular/router";
import {
  AuthenticationLogEntry,
  AuthenticationLogService
} from "@services/authentication-log/authentication-log.service";
import { AuthService } from "@services/auth/auth.service";
import { ClientsService } from "@services/clients/clients.service";
import { ConditionalAccessPolicyService } from "@services/conditional-access/conditional-access-policy.service";
import { ContentService } from "@services/content/content.service";
import { RealmService } from "@services/realm/realm.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  MockAuthenticationLogService,
  MockClientsService,
  MockConditionalAccessPolicyService,
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
  let policyService: MockConditionalAccessPolicyService;
  let authService: MockAuthService;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [AuthenticationLog],
      providers: [
        provideHttpClient(),
        // The cells that link (realm, resolver, a policy behind an outcome) instantiate routerLink, which needs an
        // ActivatedRoute.
        provideRouter([]),
        { provide: MockAuthenticationLogService, useClass: MockAuthenticationLogService },
        { provide: MockTableUtilsService, useClass: MockTableUtilsService },
        { provide: MockContentService, useClass: MockContentService },
        { provide: MockRealmService, useClass: MockRealmService },
        { provide: MockClientsService, useClass: MockClientsService },
        { provide: MockConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: AuthenticationLogService, useExisting: MockAuthenticationLogService },
        { provide: TableUtilsService, useExisting: MockTableUtilsService },
        { provide: ContentService, useExisting: MockContentService },
        { provide: RealmService, useExisting: MockRealmService },
        { provide: ClientsService, useExisting: MockClientsService },
        { provide: ConditionalAccessPolicyService, useExisting: MockConditionalAccessPolicyService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AuthenticationLog);
    component = fixture.componentInstance;
    service = TestBed.inject(MockAuthenticationLogService);
    tableUtils = TestBed.inject(MockTableUtilsService);
    clientsService = TestBed.inject(MockClientsService);
    policyService = TestBed.inject(MockConditionalAccessPolicyService);
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

  it("shows the User Role filter button for an admin and hides it in self-service", () => {
    // fixture.nativeElement is typed `any`, so it is narrowed here: an untyped call cannot take a type argument, and
    // without one the found element would be `unknown`.
    const userRoleButton = () =>
      Array.from(
        (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>(".actions-container button")
      ).find((button) => button.textContent?.includes("User Role"));
    expect(userRoleButton()).toBeTruthy();
    authService.role.set("user");
    fixture.detectChanges();
    expect(userRoleButton()).toBeFalsy();
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

  it("hasInfoValues only reports true when an entry on the page actually carries something to show", () => {
    // The table swaps in a fresh MatTableDataSource per page, so the signal must be re-set (not mutated in place) for
    // the computed to see new rows.
    const rows: AuthenticationLogEntry[] = [
      { id: 1, event_type: "LOGIN_SUCCESS", timestamp: "2026-08-03T09:00:00Z", other_info: null },
      { id: 2, event_type: "PIN_FAIL", timestamp: "2026-08-03T09:00:01Z", other_info: {} }
    ];
    component.dataSource.set(new MatTableDataSource(rows));
    expect(component.hasInfoValues()).toBe(false);

    component.dataSource.set(
      new MatTableDataSource([
        ...rows,
        {
          id: 3,
          event_type: "PIN_FAIL",
          timestamp: "2026-08-03T09:00:02Z",
          other_info: { truncated: { serial: "TOK…" } }
        }
      ])
    );
    expect(component.hasInfoValues()).toBe(true);
  });

  it("sizes each info-like column on its own content", () => {
    // The two columns are independent: a rejection row carries outcomes and no other_info, so the Conditional access
    // column must claim its width while the Info column stays narrow.
    component.dataSource.set(
      new MatTableDataSource([
        {
          id: 1,
          event_type: "USER_LOCKED",
          timestamp: "2026-08-03T09:00:00Z",
          other_info: null,
          conditional_access_outcomes: [{ policy_id: 7, policy_name: "Brute Force PIN Lockout" }]
        }
      ] as AuthenticationLogEntry[])
    );
    expect(component.hasOutcomeValues()).toBe(true);
    expect(component.hasInfoValues()).toBe(false);
    expect(component.hasColumnContent("conditional_access_outcomes")).toBe(true);
    expect(component.hasColumnContent("other_info")).toBe(false);

    // An empty list is nothing to show, like an empty other_info.
    component.dataSource.set(
      new MatTableDataSource([
        {
          id: 1,
          event_type: "LOGIN_SUCCESS",
          timestamp: "2026-08-03T09:00:00Z",
          other_info: null,
          conditional_access_outcomes: []
        }
      ] as AuthenticationLogEntry[])
    );
    expect(component.hasOutcomeValues()).toBe(false);
  });

  it("treats only the Info and Conditional access columns as info-like", () => {
    expect(component.isInfoColumn("conditional_access_outcomes")).toBe(true);
    expect(component.isInfoColumn("other_info")).toBe(true);
    expect(component.isInfoColumn("serial")).toBe(false);
  });

  // --- the Conditional access column's filter ---

  it("offers the action vocabulary and the policy names the backend serves, not a hardcoded list", () => {
    expect(component.outcomeActionOptions()).toEqual([]);
    policyService.actionTypes.set(["LOCK_USER", "BLOCK_IP"] as never);
    policyService.policies.set([
      { id: 2, name: "Notify" },
      { id: 1, name: "Brute force" },
      // Two policies can carry the same name over time; the filter offers it once.
      { id: 3, name: "Notify" }
    ] as never);

    expect(component.outcomeActionOptions()).toEqual(["LOCK_USER", "BLOCK_IP"]);
    expect(component.outcomePolicyOptions()).toEqual(["Brute force", "Notify"]);
  });

  it("falls back to typing a policy name for an admin who may not read the policies", () => {
    // Without lockout_policy_read there is no list to offer, so the menu entry has to lead somewhere else.
    const authData = authService.authData()!;
    authService.authData.set({ ...authData, rights: ["authentication_log_read", "lockout_policy_read"] });
    expect(component.canReadLockoutPolicies()).toBe(true);

    authService.authData.set({ ...authData, rights: ["authentication_log_read"] });
    expect(component.canReadLockoutPolicies()).toBe(false);
  });

  it("clearing the Conditional access filter drops all three of its keys at once", () => {
    component.setFilterValues("ca_action_type", ["LOCK_USER"]);
    component.setFilterValues("ca_policy_name", ["Brute force"]);
    component.setDryRunFilter("false");
    // A filter on another column is not part of this menu and must survive.
    component.setFilterValues("username", ["alice"]);

    component.clearOutcomeFilters();

    const filter = service.authenticationLogFilter();
    expect(filter.hasKey("ca_action_type")).toBe(false);
    expect(filter.hasKey("ca_policy_name")).toBe(false);
    expect(filter.hasKey("ca_dry_run")).toBe(false);
    expect(filter.getValueOfKey("username")).toBe("alice");
  });

  it("dry run is an exclusive choice of two values, cleared to mean both", () => {
    expect(component.dryRunOptions.map((option) => option.value)).toEqual(["false", "true"]);
    expect(component.dryRunFilter()).toBe("");
    component.setDryRunFilter("false");
    expect(service.authenticationLogFilter().getValueOfKey("ca_dry_run")).toBe("false");
    expect(component.dryRunFilter()).toBe("false");

    component.setDryRunFilter("true");
    expect(component.dryRunFilter()).toBe("true");

    // "Both" is the absence of the key, reached by clearing the filter, so nothing must be sent then.
    component.setDryRunFilter("");
    expect(service.authenticationLogFilter().hasKey("ca_dry_run")).toBe(false);
    expect(component.dryRunFilter()).toBe("");
    expect(service.filterParams()["ca_dry_run"]).toBeUndefined();
  });

  it("stores the outcome filters as ordinary filter entries", () => {
    // Which is what makes them typeable in the main filter input too; the service turns them into query params (see
    // its own spec).
    component.setFilterValues("ca_action_type", ["LOCK_USER", "BLOCK_IP"]);
    component.setFilterValues("ca_policy_name", ["Brute force"]);
    component.setDryRunFilter("false");

    const filter = service.authenticationLogFilter();
    expect(filter.getValueOfKey("ca_action_type")).toBe("LOCK_USER,BLOCK_IP");
    expect(filter.getValueOfKey("ca_policy_name")).toBe("Brute force");
    expect(filter.getValueOfKey("ca_dry_run")).toBe("false");
  });

  it("renders the Conditional access filter as one menu of its three keys, behind the shared filter icon", () => {
    policyService.actionTypes.set(["LOCK_USER"] as never);
    fixture.detectChanges();
    const header: HTMLElement = fixture.nativeElement.querySelector("th.mat-column-conditional_access_outcomes");
    const trigger: HTMLButtonElement = header.querySelector("button.filter-button")!;
    // The same icon as the other selection filters: this menu sets several keys, so it has no set/not-set state.
    expect(trigger.querySelector("mat-icon")?.textContent?.trim()).toBe("filter_list");

    // The rule that governs a combination of these filters is stated in the menu, not left to a hover tooltip, and
    // repeated on the trigger so it is announced before the menu is even opened.
    expect(trigger.getAttribute("aria-label")).toContain("All conditions must match one and the same outcome.");

    trigger.click();
    fixture.detectChanges();
    const panel: HTMLElement = document.querySelector(".mat-mdc-menu-panel")!;
    expect(panel.querySelector('[role="note"]')?.textContent).toContain(
      "All conditions must match one and the same outcome."
    );
    // A note, not an action: it must not be offered as a menu item.
    expect(panel.querySelector('button[role="note"]')).toBeNull();
    const items = Array.from(panel.querySelectorAll("button.mat-mdc-menu-item"));
    expect(items.map((item) => item.textContent?.trim())).toEqual([
      "filter_alt_offClear Filter",
      "Action",
      "Policy",
      "Dry run"
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

    // An unparsable (in-progress) edit is ignored rather than clearing an active filter.
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
    it("onRangeStartDateChange sets start_time to the start of the chosen local day and keeps the end open", () => {
      component.onRangeStartDateChange(new Date(2026, 5, 2)); // 2026-06-02, local

      const from = service.timestampFrom();
      expect(from).not.toBeNull();
      const fromDate = new Date(from!);
      // Inclusive start: local midnight of the chosen day.
      expect(fromDate.getHours()).toBe(0);
      expect(fromDate.getMinutes()).toBe(0);
      expect(fromDate.getSeconds()).toBe(0);
      expect(service.timestampTo()).toBeNull();
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(true);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(false);
      // Filter display value includes local UTC offset (e.g. +00:00, +02:00).
      expect(service.authenticationLogFilter().getValueOfKey("start_time")).toMatch(/( [+-]\d{2}:\d{2}| Z)$/);
    });

    it("onRangeEndDateChange sets end_time to the end of the chosen local day and keeps the start bound", () => {
      component.onRangeStartDateChange(new Date(2026, 5, 2));
      component.onRangeEndDateChange(new Date(2026, 5, 5));

      expect(service.timestampFrom()).not.toBeNull();
      const to = new Date(service.timestampTo()!);
      // Inclusive end: local 23:59:59 of the chosen day.
      expect(to.getHours()).toBe(23);
      expect(to.getMinutes()).toBe(59);
      expect(to.getSeconds()).toBe(59);
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(true);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(true);
    });

    it("selecting a single day zooms the slider window to that 24h span (thumbs at the extremes)", () => {
      const day = new Date(2026, 5, 2);
      component.onRangeStartDateChange(day);
      component.onRangeEndDateChange(day);

      // The window now spans just the selected day, so the from/to thumbs sit at the very edges of the track.
      expect(component.rangeStart()).toBe(0);
      expect(component.rangeEnd()).toBe(component.rangeSliderSteps);
      // Window span is one local day (00:00:00 -> 23:59:59), i.e. within a second of 24 hours.
      const span = component.windowEndMs() - component.windowStartMs();
      expect(span).toBeGreaterThan(23 * 3_600_000);
      expect(span).toBeLessThanOrEqual(86_400_000);
      // The end thumb at its max now maps to the concrete day-end, not an open "now" bound.
      expect(service.timestampTo()).not.toBeNull();
    });

    it("dateRangeLabel is the neutral default, a matched preset name, or the custom fallback", () => {
      expect(component.dateRangeLabel()).toBe("Date range");

      // A start ~1 year ago with an open end reads as the "Last year" preset.
      const yearAgo = new Date();
      yearAgo.setDate(yearAgo.getDate() - 365);
      component.onRangeStartDateChange(yearAgo);
      expect(component.dateRangeLabel()).toBe("Last year");

      // A bounded historical range that does not end near now is a plain custom range.
      component.onRangeStartDateChange(new Date(2020, 0, 1));
      component.onRangeEndDateChange(new Date(2020, 0, 15));
      expect(component.dateRangeLabel()).toBe("Custom range");
    });

    it("narrowing the slider keeps the picker range at the window min/max", () => {
      component.onRangeStartDateChange(new Date(2026, 5, 1));
      component.onRangeEndDateChange(new Date(2026, 5, 5));
      const startBefore = component.rangePickerStart()!.getTime();
      const endBefore = component.rangePickerEnd()!.getTime();

      // Narrow the selection with the slider thumbs and commit.
      component.onRangeStartInput(50);
      component.onRangeEndInput(150);
      component.commitTimeRange();

      // The picker still reflects the window bounds, unchanged by the slider...
      expect(component.rangePickerStart()!.getTime()).toBe(startBefore);
      expect(component.rangePickerEnd()!.getTime()).toBe(endBefore);
      // ...while the actual filter narrowed inside that window.
      expect(new Date(service.timestampFrom()!).getTime()).toBeGreaterThan(startBefore);
      expect(new Date(service.timestampTo()!).getTime()).toBeLessThan(endBefore);
    });

    it("clearing a picker field (null) drops that bound and keeps the other", () => {
      component.onRangeStartDateChange(new Date(2026, 5, 2));
      component.onRangeEndDateChange(new Date(2026, 5, 5));
      component.onRangeStartDateChange(null);

      expect(service.timestampFrom()).toBeNull();
      expect(service.timestampTo()).not.toBeNull();
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(false);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(true);
    });

    it("rangePickerStart/End mirror the active time filter as Dates", () => {
      expect(component.rangePickerStart()).toBeNull();
      expect(component.rangePickerEnd()).toBeNull();

      component.onRangeStartDateChange(new Date(2026, 5, 2));

      expect(component.rangePickerStart()).toBeInstanceOf(Date);
      expect(component.rangePickerEnd()).toBeNull();
    });

    it("clearTimeFilter resets from, to and removes keys from filter text", () => {
      component.onRangeStartDateChange(new Date(2026, 5, 2));
      component.clearTimeFilter();

      expect(service.timestampFrom()).toBeNull();
      expect(service.timestampTo()).toBeNull();
      expect(service.authenticationLogFilter().hasKey("start_time")).toBe(false);
      expect(service.authenticationLogFilter().hasKey("end_time")).toBe(false);
    });

    it("clearAllFilters clears both the text filter and the time filter", () => {
      // A time filter lives in its own signals; clearing the text alone used to leave it silently active.
      service.authenticationLogFilter.set(service.authenticationLogFilter().copyWith({ value: "username: alice" }));
      component.onRangeStartDateChange(new Date(2026, 5, 2));
      expect(service.timestampFrom()).not.toBeNull();

      component.clearAllFilters();

      expect(service.timestampFrom()).toBeNull();
      expect(service.timestampTo()).toBeNull();
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
