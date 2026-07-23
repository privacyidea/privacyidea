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
import { BlocklistComponent } from "./blocklist.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { ConditionalAccessStateService } from "@services/conditional-access-state/conditional-access-state.service";
import { MockAuthService, MockDialogService, MockNotificationService } from "@testing/mock-services";
import { MockConditionalAccessStateService } from "@testing/mock-services/mock-conditional-access-state-service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { BlocklistEntry } from "@services/conditional-access-state/conditional-access-state.service";

const activeEntry: BlocklistEntry = {
  identifier: "192.168.1.100",
  block_expires_at: "2026-12-31T23:59:59Z",
  seconds_remaining: 3600,
  is_blocked: true,
  permanent: false,
  reason: "Too many failed auth attempts",
  last_updated: "2026-01-01T09:00:00Z"
};

const permanentEntry: BlocklistEntry = {
  identifier: "10.0.0.1",
  block_expires_at: null,
  seconds_remaining: null,
  is_blocked: true,
  permanent: true,
  reason: "Permanently blocked",
  last_updated: "2026-01-01T08:00:00Z"
};

const expiredEntry: BlocklistEntry = {
  identifier: "172.16.0.5",
  block_expires_at: "2025-06-01T00:00:00Z",
  seconds_remaining: 0,
  is_blocked: true,
  permanent: false,
  reason: "Expired block",
  last_updated: "2025-05-01T00:00:00Z"
};

describe("BlocklistComponent", () => {
  let fixture: ComponentFixture<BlocklistComponent>;
  let component: BlocklistComponent;
  let casService: MockConditionalAccessStateService;
  let dialogService: MockDialogService;
  let notificationService: MockNotificationService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [BlocklistComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ConditionalAccessStateService, useClass: MockConditionalAccessStateService },
        provideHttpClient()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(BlocklistComponent);
    component = fixture.componentInstance;
    casService = TestBed.inject(ConditionalAccessStateService) as unknown as MockConditionalAccessStateService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should be created", () => {
    expect(component).toBeTruthy();
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
    component.filterText = "test";
    component.dataSource().filter = "test";
    component.clearFilter();
    expect(component.filterText).toBe("");
    expect(component.dataSource().filter).toBe("");
  });
});
