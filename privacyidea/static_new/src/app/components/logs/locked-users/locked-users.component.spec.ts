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
import { LockedUsersComponent } from "./locked-users.component";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { ConditionalAccessStateService } from "@services/conditional-access-state/conditional-access-state.service";
import { AuthenticationLogService } from "@services/authentication-log/authentication-log.service";
import {
  MockAuthService,
  MockAuthenticationLogService,
  MockContentService,
  MockDialogService,
  MockNotificationService,
  MockRealmService,
  MockTableUtilsService
} from "@testing/mock-services";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { MockConditionalAccessStateService } from "@testing/mock-services/mock-conditional-access-state-service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { LockedUserEntry } from "@services/conditional-access-state/conditional-access-state.service";

const mockEntry: LockedUserEntry = {
  resolver: "ldapResolver",
  uid: "uid001",
  realm: "myrealm",
  username: "alice",
  permanent: false,
  lock_expires_at: "2026-01-01T10:00:00Z",
  seconds_remaining: 3600,
  locked_at: "2026-01-01T09:00:00Z",
  error_message: null
};

const permanentEntry: LockedUserEntry = {
  ...mockEntry,
  username: "bob",
  uid: "uid002",
  permanent: true,
  lock_expires_at: null,
  seconds_remaining: null
};

const expiredEntry: LockedUserEntry = {
  ...mockEntry,
  username: "carol",
  uid: "uid003",
  permanent: false,
  seconds_remaining: 0
};

describe("LockedUsersComponent", () => {
  let fixture: ComponentFixture<LockedUsersComponent>;
  let component: LockedUsersComponent;
  let casService: MockConditionalAccessStateService;
  let dialogService: MockDialogService;
  let notificationService: MockNotificationService;
  let tableUtilsService: MockTableUtilsService;
  let authLogService: MockAuthenticationLogService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [LockedUsersComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ConditionalAccessStateService, useClass: MockConditionalAccessStateService },
        { provide: AuthenticationLogService, useClass: MockAuthenticationLogService },
        provideHttpClient()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LockedUsersComponent);
    component = fixture.componentInstance;
    casService = TestBed.inject(ConditionalAccessStateService) as unknown as MockConditionalAccessStateService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    tableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
    authLogService = TestBed.inject(AuthenticationLogService) as unknown as MockAuthenticationLogService;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should be created", () => {
    expect(component).toBeTruthy();
  });

  describe("showAuthenticationLog", () => {
    it("seeds the auth-log filter with username, realm and resolver", () => {
      component.showAuthenticationLog(mockEntry);
      const filter = authLogService.authenticationLogFilter().filterMap;
      expect(filter.get("username")).toBe("alice");
      expect(filter.get("realm")).toBe("myrealm");
      expect(filter.get("resolver")).toBe("ldapResolver");
      expect(filter.has("uid")).toBe(false);
    });

    it("falls back to uid when the row has no username", () => {
      component.showAuthenticationLog({ ...mockEntry, username: "" });
      const filter = authLogService.authenticationLogFilter().filterMap;
      expect(filter.get("uid")).toBe("uid001");
      expect(filter.has("username")).toBe(false);
      expect(filter.get("realm")).toBe("myrealm");
      expect(filter.get("resolver")).toBe("ldapResolver");
    });
  });

  it("dataSource is empty when the resource has no value", () => {
    casService.setLockedUsersResourceUndefined();
    expect(component.dataSource().data).toEqual([]);
  });

  it("dataSource reflects the resource value", () => {
    casService.setLockedUsers([mockEntry]);
    expect(component.dataSource().data).toEqual([mockEntry]);
  });

  it("keeps the previous rows while the resource reloads (no flicker)", () => {
    casService.setLockedUsers([mockEntry]);
    expect(component.dataSource().data).toEqual([mockEntry]);
    // Simulate an in-flight reload: the resource temporarily has no value.
    casService.setLockedUsersResourceUndefined();
    expect(component.dataSource().data).toEqual([mockEntry]);
  });

  it("displayLogin returns the username, or the uid as fallback", () => {
    expect(component.displayLogin(mockEntry)).toBe("alice");
    expect(component.displayLogin({ ...mockEntry, username: "" })).toBe("uid001");
  });

  it("isExpired is false for active and permanent locks, true for elapsed timed locks", () => {
    expect(component.isExpired(mockEntry)).toBe(false);
    expect(component.isExpired(permanentEntry)).toBe(false);
    expect(component.isExpired(expiredEntry)).toBe(true);
  });

  it("lock-state badge is red/permanent, orange/active, green/expired", () => {
    expect(component.lockStateClass(permanentEntry)).toBe("highlight-false");
    expect(component.lockStateClass(mockEntry)).toBe("highlight-warning");
    expect(component.lockStateClass(expiredEntry)).toBe("highlight-true");
    expect(component.lockStateLabel(permanentEntry)).toBe("Permanent");
    expect(component.lockStateLabel(mockEntry)).toBe("Temporary");
    expect(component.lockStateLabel(expiredEntry)).toBe("Expired");
  });

  it("onKeywordClick delegates to the table-utils keyword toggler and stores the result", () => {
    const toggled = new FilterValue({ value: "usernames: " });
    (tableUtilsService.toggleKeywordInFilter as jest.Mock).mockReturnValue(toggled);
    component.onKeywordClick("usernames");
    expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
      keyword: "usernames",
      currentValue: expect.any(FilterValue)
    });
    expect(casService.lockedUsersFilter()).toBe(toggled);
  });

  it("onKeywordClick focuses the filter input so the value can be typed right away", () => {
    (tableUtilsService.toggleKeywordInFilter as jest.Mock).mockReturnValue(new FilterValue({ value: "usernames: " }));
    const focusSpy = jest.spyOn(component.filterInput.nativeElement, "focus");

    component.onKeywordClick("usernames");

    expect(focusSpy).toHaveBeenCalled();
  });

  it("sets and reads the state filter", () => {
    component.setFilterValues("states", ["expired"]);
    expect(component.selectedFilterValues("states")).toEqual(["expired"]);
  });

  it("selects and deselects rows", () => {
    casService.setLockedUsers([mockEntry, permanentEntry]);
    component.toggleRow(mockEntry);
    expect(component.selection()).toEqual([mockEntry]);
    component.toggleAllRows();
    expect(component.selection().length).toBe(2);
    expect(component.isAllSelected()).toBe(true);
    component.toggleAllRows();
    expect(component.selection()).toEqual([]);
  });

  it("resets the selected locks after confirmation", () => {
    casService.setLockedUsers([mockEntry, permanentEntry]);
    component.selection.set([mockEntry, permanentEntry]);
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);
    (casService.resetUserLock as jest.Mock).mockReturnValue(of(true));

    component.resetSelected();
    dialogRef.close(true);

    expect(dialogService.openDialog).toHaveBeenCalled();
    expect(casService.resetUserLock).toHaveBeenCalledTimes(2);
    expect(casService.resetUserLock).toHaveBeenCalledWith({
      uid: mockEntry.uid,
      realm: mockEntry.realm,
      resolver: mockEntry.resolver
    });
    expect(notificationService.success).toHaveBeenCalled();
    expect(casService.lockedUsersResource.reload).toHaveBeenCalled();
  });

  it("does NOT reset when the dialog is cancelled", () => {
    component.selection.set([mockEntry]);
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);

    component.resetSelected();
    dialogRef.close(false);

    expect(casService.resetUserLock).not.toHaveBeenCalled();
  });

  it("does nothing when resetSelected is called with an empty selection", () => {
    component.selection.set([]);
    component.resetSelected();
    expect(dialogService.openDialog).not.toHaveBeenCalled();
  });

  it("sets and reads filter values (CSV per key)", () => {
    component.setFilterValues("realms", ["r1", "r2"]);
    expect(component.selectedFilterValues("realms")).toEqual(["r1", "r2"]);
    component.setFilterValues("realms", []);
    expect(component.selectedFilterValues("realms")).toEqual([]);
  });

  it("addFilterValue appends without duplicates (username fast filter)", () => {
    component.addFilterValue("usernames", "alice");
    component.addFilterValue("usernames", "alice");
    component.addFilterValue("usernames", "bob");
    expect(component.selectedFilterValues("usernames")).toEqual(["alice", "bob"]);
  });

  it("onSortClick delegates to the table-utils sort cycler", () => {
    component.onSortClick("locked_at");
    expect(tableUtilsService.onSortButtonClick).toHaveBeenCalledWith("locked_at", casService.lockedUsersSort, {
      active: "locked_at",
      direction: ""
    });
  });

  it("onPageEvent updates page size and the 1-based page index", () => {
    component.onPageEvent({ pageIndex: 2, pageSize: 25, length: 100, previousPageIndex: 0 });
    expect(casService.lockedUsersPageSize()).toBe(25);
    expect(casService.lockedUsersPageIndex()).toBe(3);
  });

  it("totalLength reflects the resource count", () => {
    casService.setLockedUsers([mockEntry, permanentEntry]);
    expect(component.totalLength()).toBe(2);
  });

  it("confirms, then deletes expired locks and reloads", () => {
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);
    (casService.purgeUserLocks as jest.Mock).mockReturnValue(of(3));

    component.deleteExpired();
    dialogRef.close(true);

    expect(dialogService.openDialog).toHaveBeenCalled();
    expect(casService.purgeUserLocks).toHaveBeenCalled();
    expect(notificationService.success).toHaveBeenCalled();
    expect(casService.lockedUsersResource.reload).toHaveBeenCalled();
  });

  it("does NOT purge when the delete-expired dialog is cancelled", () => {
    const dialogRef = new MockMatDialogRef<unknown, boolean>();
    (dialogService.openDialog as jest.Mock).mockReturnValue(dialogRef);

    component.deleteExpired();
    dialogRef.close(false);

    expect(casService.purgeUserLocks).not.toHaveBeenCalled();
  });

  it("handleFilterInput writes the raw input into the shared filter", () => {
    component.handleFilterInput({ target: { value: "usernames: alice" } } as unknown as Event);
    expect(casService.lockedUsersFilter().getValueOfKey("usernames")).toBe("alice");
  });

  it("lists the stored wording as a column", () => {
    // An admin looking at a locked user should see what that user is actually told, without opening the policy -
    // and the row carries the message stored at lock time, not what the stage says now. Material throws on a
    // displayed column with no matColumnDef, so this also covers the template wiring.
    casService.setLockedUsers([
      { ...mockEntry, error_message: "Locked. Try again in about {duration}." },
      { ...mockEntry, username: "bob", uid: "uid002" }
    ]);
    expect(component.displayedColumns).toContain("error_message");
    const byUser = new Map(component.dataSource().data.map((row) => [row.username, row.error_message]));
    expect(byUser.get("alice")).toBe("Locked. Try again in about {duration}.");
    expect(byUser.get("bob")).toBeNull();
  });

  it("clearFilter empties the shared filter", () => {
    casService.lockedUsersFilter.set(new FilterValue({ value: "usernames: alice" }));
    component.clearFilter();
    expect(casService.lockedUsersFilter().getValueOfKey("usernames")).toBeFalsy();
  });
});
