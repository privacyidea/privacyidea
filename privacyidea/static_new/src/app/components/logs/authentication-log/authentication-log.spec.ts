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

import { AuthenticationLog } from "./authentication-log";

describe("AuthenticationLog", () => {
  let component: AuthenticationLog;
  let fixture: ComponentFixture<AuthenticationLog>;
  let service: MockAuthenticationLogService;
  let tableUtils: MockTableUtilsService;
  let clientsService: MockClientsService;

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
    fixture.detectChanges();
  });

  it("creates and exposes one column key per column definition", () => {
    expect(component).toBeTruthy();
    expect(component.columnKeys.length).toBe(component.columnKeysMap.length);
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

  it("onSortClick cycles a column through ascending -> descending -> cleared (default)", () => {
    component.onSortClick("event_type");
    expect(service.sort()).toEqual({ active: "event_type", direction: "asc" });

    component.onSortClick("event_type");
    expect(service.sort()).toEqual({ active: "event_type", direction: "desc" });

    // Third click clears to the default order with a neutral (empty) direction.
    component.onSortClick("event_type");
    expect(service.sort()).toEqual({ active: "timestamp", direction: "" });

    // Switching to another column starts ascending again.
    component.onSortClick("username");
    expect(service.sort()).toEqual({ active: "username", direction: "asc" });
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

  it("formatInfo serializes other_info and tolerates null", () => {
    expect(component.formatInfo({ a: 1 })).toBe('{"a":1}');
    expect(component.formatInfo(null)).toBe("");
  });

  it("setFilterValues stores a multi-value selection as CSV", () => {
    component.setFilterValues("event_type", ["LOGIN_SUCCESS", "MFA_FAIL"]);
    expect(service.authenticationLogFilter().getValueOfKey("event_type")).toBe("LOGIN_SUCCESS,MFA_FAIL");
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

  it("exposes the full set of event-type options", () => {
    expect(component.eventTypeOptions).toContain("LOGIN_SUCCESS");
    expect(component.eventTypeOptions).toContain("UNKNOWN_FAIL_REASON");
    expect(component.eventTypeOptions.length).toBe(17);
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

  it("splitSerials splits comma-separated serials, trims, and drops blanks", () => {
    expect(component.splitSerials("PISP0001")).toEqual(["PISP0001"]);
    expect(component.splitSerials("PISP0001, PISP0002 ,PISP0003")).toEqual(["PISP0001", "PISP0002", "PISP0003"]);
    expect(component.splitSerials("PISP0001,,")).toEqual(["PISP0001"]);
    expect(component.splitSerials("")).toEqual([]);
    expect(component.splitSerials(null)).toEqual([]);
  });
});
