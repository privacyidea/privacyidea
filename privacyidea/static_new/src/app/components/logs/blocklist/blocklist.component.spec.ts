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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import {
  BlocklistBlockDialogComponent,
  BlocklistBlockDialogResult
} from "./blocklist-block-dialog/blocklist-block-dialog.component";
import { BlocklistComponent } from "./blocklist.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { ConditionalAccessStateService } from "@services/conditional-access-state/conditional-access-state.service";
import { AuthenticationLogService } from "@services/authentication-log/authentication-log.service";
import {
  MockAuthService,
  MockAuthenticationLogService,
  MockDialogService,
  MockNotificationService
} from "@testing/mock-services";
import { MockConditionalAccessStateService } from "@testing/mock-services/mock-conditional-access-state-service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { BlocklistEntry } from "@services/conditional-access-state/conditional-access-state.service";

const activeEntry: BlocklistEntry = {
  identifier: "192.168.1.100",
  block_expires_at: "2026-12-31T23:59:59Z",
  seconds_remaining: 3600,
  permanent: false,
  block_cause: "POLICY",
  blocked_at: "2026-01-01T09:00:00Z",
  error_message: "Your address is blocked. Try again in about {duration}."
};

const permanentEntry: BlocklistEntry = {
  identifier: "10.0.0.1",
  block_expires_at: null,
  seconds_remaining: null,
  permanent: true,
  block_cause: "POLICY",
  blocked_at: "2026-01-01T08:00:00Z",
  error_message: null
};

const expiredEntry: BlocklistEntry = {
  identifier: "172.16.0.5",
  block_expires_at: "2025-06-01T00:00:00Z",
  seconds_remaining: 0,
  permanent: false,
  block_cause: "POLICY",
  blocked_at: "2025-05-01T00:00:00Z",
  error_message: null
};

describe("BlocklistComponent", () => {
  let fixture: ComponentFixture<BlocklistComponent>;
  let component: BlocklistComponent;
  let casService: MockConditionalAccessStateService;
  let dialogService: MockDialogService;
  let notificationService: MockNotificationService;
  let authLogService: MockAuthenticationLogService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [BlocklistComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ConditionalAccessStateService, useClass: MockConditionalAccessStateService },
        { provide: AuthenticationLogService, useClass: MockAuthenticationLogService },
        provideHttpClient()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(BlocklistComponent);
    component = fixture.componentInstance;
    casService = TestBed.inject(ConditionalAccessStateService) as unknown as MockConditionalAccessStateService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    authLogService = TestBed.inject(AuthenticationLogService) as unknown as MockAuthenticationLogService;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should be created", () => {
    expect(component).toBeTruthy();
  });

  it("showAuthenticationLog seeds the auth-log filter with the source IP", () => {
    component.showAuthenticationLog(activeEntry);
    const filter = authLogService.authenticationLogFilter().filterMap;
    expect(filter.get("source_ip")).toBe("192.168.1.100");
  });

  it("dataSource is empty when the resource has no value", () => {
    casService.setBlocklistResourceUndefined();
    expect(component.dataSource().data).toEqual([]);
  });

  it("dataSource reflects the flat list resource value", () => {
    casService.setBlocklistEntries([activeEntry]);
    expect(component.dataSource().data).toEqual([activeEntry]);
  });

  it("keeps the previous rows while the resource reloads (no flicker)", () => {
    casService.setBlocklistEntries([activeEntry]);
    expect(component.dataSource().data).toEqual([activeEntry]);
    casService.setBlocklistResourceUndefined();
    expect(component.dataSource().data).toEqual([activeEntry]);
  });

  it("buildState returns the correct state for each entry", () => {
    expect(component.blockState(permanentEntry)).toBe("permanent");
    expect(component.blockState(activeEntry)).toBe("temporary");
    expect(component.blockState(expiredEntry)).toBe("expired");
  });

  it("isExpired returns false for active and permanent entries, true for elapsed timed entries", () => {
    expect(component.isExpired(activeEntry)).toBe(false);
    expect(component.isExpired(permanentEntry)).toBe(false);
    expect(component.isExpired(expiredEntry)).toBe(true);
  });

  it("selects and deselects rows", () => {
    casService.setBlocklistEntries([activeEntry, permanentEntry]);
    component.toggleRow(activeEntry);
    expect(component.selection()).toEqual([activeEntry]);
    component.toggleAllRows();
    expect(component.selection().length).toBe(2);
    expect(component.isAllSelected()).toBe(true);
    component.toggleAllRows();
    expect(component.selection()).toEqual([]);
  });

  it("text filter searches across all columns (case-insensitive)", () => {
    casService.setBlocklistEntries([activeEntry, permanentEntry, expiredEntry]);
    component.handleFilterInput({ target: { value: "192.168" } } as unknown as Event);
    expect(component.dataSource().filteredData).toEqual([activeEntry]);
  });

  it("confirms, then removes selected entries and reloads", () => {
    casService.setBlocklistEntries([activeEntry, permanentEntry]);
    component.selection.set([activeEntry, permanentEntry]);
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);
    (casService.removeBlocklistEntry as jest.Mock).mockReturnValue(of(true));

    component.removeSelected();
    dialogRef.close(true);

    expect(dialogService.openDialog).toHaveBeenCalled();
    expect(casService.removeBlocklistEntry).toHaveBeenCalledTimes(2);
    expect(casService.removeBlocklistEntry).toHaveBeenCalledWith(activeEntry);
    expect(notificationService.success).toHaveBeenCalled();
    expect(casService.blocklistResource.reload).toHaveBeenCalled();
  });

  it("blocks an IP from the dialog and reloads", () => {
    const dialogRef = new MockMatDialogRef<unknown, BlocklistBlockDialogResult>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);

    component.blockIp();
    dialogRef.close({ ip: "203.0.113.42", durationSeconds: 600 });

    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({ component: BlocklistBlockDialogComponent })
    );
    expect(casService.addBlocklistEntry).toHaveBeenCalledWith({ ip: "203.0.113.42", duration_seconds: 600 });
    expect(casService.blocklistResource.reload).toHaveBeenCalled();
  });

  it("omits the duration for a permanent block", () => {
    const dialogRef = new MockMatDialogRef<unknown, BlocklistBlockDialogResult>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);

    component.blockIp();
    dialogRef.close({ ip: "203.0.113.42", durationSeconds: null });

    expect(casService.addBlocklistEntry).toHaveBeenCalledWith({ ip: "203.0.113.42", duration_seconds: undefined });
  });

  it("does NOT block when the dialog is cancelled", () => {
    const dialogRef = new MockMatDialogRef<unknown, BlocklistBlockDialogResult>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);

    component.blockIp();
    dialogRef.close(null as never);

    expect(casService.addBlocklistEntry).not.toHaveBeenCalled();
  });

  it("labels who imposed the block", () => {
    expect(component.blockCauseLabel({ ...activeEntry, block_cause: "MANUAL" })).toBe("Manual");
    expect(component.blockCauseLabel({ ...activeEntry, block_cause: "POLICY" })).toBe("Policy");
  });

  it("does NOT remove when the dialog is cancelled", () => {
    component.selection.set([activeEntry]);
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);

    component.removeSelected();
    dialogRef.close(false);

    expect(casService.removeBlocklistEntry).not.toHaveBeenCalled();
  });

  it("does nothing when removeSelected is called with an empty selection", () => {
    component.selection.set([]);
    component.removeSelected();
    expect(dialogService.openDialog).not.toHaveBeenCalled();
  });

  it("confirms, then purges expired entries and reloads", () => {
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);
    (casService.purgeBlocklist as jest.Mock).mockReturnValue(of(2));

    component.cleanUpExpired();
    dialogRef.close(true);

    expect(dialogService.openDialog).toHaveBeenCalled();
    expect(casService.purgeBlocklist).toHaveBeenCalled();
    expect(notificationService.success).toHaveBeenCalled();
    expect(casService.blocklistResource.reload).toHaveBeenCalled();
  });

  it("does NOT purge when the clean-up dialog is cancelled", () => {
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);

    component.cleanUpExpired();
    dialogRef.close(false);

    expect(casService.purgeBlocklist).not.toHaveBeenCalled();
  });

  it("clearFilter resets the filter text", () => {
    component.filterText.set("test");
    component.dataSource().filter = "test";
    component.clearFilter();
    expect(component.filterText()).toBe("");
    expect(component.dataSource().filter).toBe("");
  });

  it("keeps the active filter when the blocklist is reloaded", () => {
    casService.setBlocklistEntries([activeEntry, permanentEntry]);
    component.handleFilterInput({ target: { value: "10.0.0.1" } } as unknown as Event);
    expect(component.dataSource().filteredData).toEqual([permanentEntry]);

    // A reload builds a new data source; the filter must survive it.
    casService.setBlocklistEntries([activeEntry, permanentEntry]);

    expect(component.dataSource().filter).toBe("10.0.0.1");
    expect(component.dataSource().filteredData).toEqual([permanentEntry]);
  });

  it("blockStateClass maps permanent/expired/temporary to the badge colours", () => {
    expect(component.blockStateClass(permanentEntry)).toBe("highlight-false");
    expect(component.blockStateClass(expiredEntry)).toBe("highlight-true");
    expect(component.blockStateClass(activeEntry)).toBe("highlight-warning");
  });

  it("the filter predicate keeps every row when the filter is empty", () => {
    const predicate = component.blockFilterPredicate();
    expect(predicate(activeEntry, "")).toBe(true);
  });

  it("the filter predicate also matches on the state word", () => {
    const predicate = component.blockFilterPredicate();
    expect(predicate(permanentEntry, "permanent")).toBe(true);
    expect(predicate(activeEntry, "permanent")).toBe(false);
  });

  it("onSortEvent sorts by identifier (string compare via the default branch)", () => {
    casService.setBlocklistEntries([activeEntry, permanentEntry, expiredEntry]);
    // The default sort is identifier/asc, so the first click flips it to desc.
    component.onSortEvent("identifier");
    expect(component.sort()).toEqual({ active: "identifier", direction: "desc" });
    // Descending string order: "192.168.1.100" > "172.16.0.5" > "10.0.0.1".
    expect(component.dataSource().data[0]).toBe(activeEntry);
    expect(component.dataSource().data[2]).toBe(permanentEntry);
  });

  it("onSortEvent cycles a non-default column asc -> desc -> reset to default", () => {
    casService.setBlocklistEntries([activeEntry, permanentEntry, expiredEntry]);

    component.onSortEvent("blocked_at");
    expect(component.sort()).toEqual({ active: "blocked_at", direction: "asc" });

    component.onSortEvent("blocked_at");
    expect(component.sort()).toEqual({ active: "blocked_at", direction: "desc" });

    // Third click clears the direction and falls back to the default sort.
    component.onSortEvent("blocked_at");
    expect(component.sort()).toEqual({ active: "identifier", direction: "asc" });
  });

  it("onSortEvent sorts by the numeric expiry and the derived state column", () => {
    casService.setBlocklistEntries([activeEntry, permanentEntry, expiredEntry]);
    component.onSortEvent("block_expires_at");
    expect(component.sort().active).toBe("block_expires_at");
    component.onSortEvent("state");
    expect(component.sort().active).toBe("state");
    expect(component.dataSource().data.length).toBe(3);
  });

  it("lists the stored wording as a column", () => {
    // An admin looking at a blocked address should see what that address is actually told, without opening the
    // policy - and the row carries the message stored at block time, not what the stage says now.
    // Material throws on a displayed column with no matColumnDef, and the table renders here, so this also
    // covers the template wiring.
    casService.setBlocklistEntries([activeEntry, permanentEntry]);
    expect(component.displayedColumns).toContain("error_message");
    const byIp = new Map(component.dataSource().data.map((row) => [row.identifier, row.error_message]));
    expect(byIp.get(activeEntry.identifier)).toBe("Your address is blocked. Try again in about {duration}.");
    expect(byIp.get(permanentEntry.identifier)).toBeNull();
  });

  it("matches the stored wording in the free-text filter", () => {
    // The blocklist filters client-side, so the message has to be part of the predicate for an admin to find
    // every address still quoting wording they have since changed.
    casService.setBlocklistEntries([activeEntry, permanentEntry]);
    const predicate = component.blockFilterPredicate();
    expect(predicate(activeEntry, "try again")).toBe(true);
    expect(predicate(permanentEntry, "try again")).toBe(false);
  });

  it("getSortIcon reflects the active column and direction", () => {
    // identifier/asc is the default active sort; an unrelated column is neutral.
    expect(component.getSortIcon("blocked_at")).toBe("unfold_more");
    expect(component.getSortIcon("identifier")).toBe("keyboard_arrow_upward");
    component.onSortEvent("identifier"); // -> desc
    expect(component.getSortIcon("identifier")).toBe("keyboard_arrow_downward");
  });
});
