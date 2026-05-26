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
import { ElementRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BehaviorSubject, map, of } from "rxjs";

import { BreakpointObserver } from "@angular/cdk/layout";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { UserDetailsComponent } from "./user-details.component";

import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute } from "@angular/router";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import {
  MockAuditService,
  MockContainerService,
  MockContentService,
  MockDialogService,
  MockLocalService,
  MockMatDialog,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";

describe("UserDetailsComponent", () => {
  let component: UserDetailsComponent;
  let fixture: ComponentFixture<UserDetailsComponent>;

  let userServiceMock: MockUserService;
  let tokenServiceMock: MockTokenService;
  let dialogServiceMock: MockDialogService;
  let pendingChangesService: MockPendingChangesService;
  let dialogMock: MockMatDialog;
  let breakpointSubject: BehaviorSubject<Record<string, boolean>>;

  const mockUserData = {
    username: "alice",
    resolver: "default",
    description: "",
    editable: true,
    email: "alice@example.com",
    givenname: "Alice",
    surname: "Smith",
    userid: "u123",
    mobile: "",
    phone: ""
  };

  beforeEach(async () => {
    TestBed.resetTestingModule();

    dialogMock = new MockMatDialog();
    breakpointSubject = new BehaviorSubject<Record<string, boolean>>({
      "(max-width: 1000px)": false,
      "(max-width: 1240px)": false
    });

    await TestBed.configureTestingModule({
      imports: [UserDetailsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: BreakpointObserver,
          useValue: {
            observe: (query: string) =>
              breakpointSubject.pipe(map((b) => ({ matches: b[query] || false, breakpoints: {} })))
          }
        },
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: UserService, useClass: MockUserService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: MatDialog, useValue: dialogMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();
    jest.useFakeTimers();

    fixture = TestBed.createComponent(UserDetailsComponent);
    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  const getHasChangesFn = () =>
    (pendingChangesService.registerHasChanges as jest.Mock).mock.calls[0][0] as () => boolean;
  const getValidChangesFn = () =>
    (pendingChangesService.registerValidChanges as jest.Mock).mock.calls[0][0] as () => boolean;
  const getSaveFn = () => (pendingChangesService.registerSave as jest.Mock).mock.calls[0][0] as () => Promise<boolean>;

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("tokenDataSource populates from tokenResource and keeps previous when resource is missing", () => {
    tokenServiceMock.tokenResourceValue.set({
      count: 2,
      current: 2,
      tokens: [
        { serial: "T-1", revoked: false, locked: false } as TokenDetails,
        { serial: "T-2", revoked: false, locked: false } as TokenDetails
      ]
    });
    fixture.detectChanges();

    expect(component.tokenDataSource().data.map((t) => t.serial)).toEqual(["T-1", "T-2"]);
    expect(component.total()).toBe(2);

    tokenServiceMock.tokenResource.value.set(undefined);
    fixture.detectChanges();

    expect(component.tokenDataSource().data.map((t) => t.serial)).toEqual(["T-1", "T-2"]);
    expect(component.total()).toBe(2);
  });

  it("switches key mode between input/select as expected", () => {
    expect(component.keyMode()).toBe("select");

    component.switchToCustomKey();
    expect(component.keyMode()).toBe("input");
    expect(component.selectedKey()).toBeNull();

    component.switchToSelectKey();
    expect(component.keyMode()).toBe("select");
    expect(component.addKeyInput()).toBe("");
  });

  it("valueOptions / isValueInput / canAddAttribute computed helpers", () => {
    userServiceMock.attributeSetMap.set({
      department: ["sales", "finance"],
      customKey: ["2", "1"]
    });
    component.selectedKey.set("department");
    expect(component.valueOptions()).toEqual(["sales", "finance"]);
    expect(component.isValueInput()).toBe(false);

    component.selectedValue.set("sales");
    expect(component.canAddAttribute()).toBe(true);

    component.switchToCustomKey();
    component.addKeyInput.set("customKey");
    expect(component.valueOptions()).toEqual(["2", "1"]);
    expect(component.isValueInput()).toBe(false);

    component.selectedValue.set("");
    expect(component.canAddAttribute()).toBe(false);
    component.selectedValue.set("foo");
    expect(component.canAddAttribute()).toBe(true);
  });

  it("addCustomAttribute calls setUserAttribute and reloads userAttributesResource, then clears inputs", async () => {
    userServiceMock.attributeSetMap.set({
      department: ["sales", "finance"],
      customKey: ["2", "1"]
    });
    component.selectedKey.set("department");
    component.selectedValue.set("sales");

    const setSpy = jest.spyOn(userServiceMock, "setUserAttribute");
    const reloadSpy = jest.spyOn(userServiceMock.userAttributesResource, "reload");

    const result = await component.addCustomAttribute();
    expect(result).toBe(true);
    expect(setSpy).toHaveBeenCalledWith("department", "sales");
    expect(reloadSpy).toHaveBeenCalledTimes(1);

    expect(component.addKeyInput()).toBe("");
    expect(component.addValueInput()).toBe("");
    expect(component.selectedKey()).toBeNull();
    expect(component.selectedValue()).toBeNull();
  });

  it("deleteCustomAttribute calls deleteUserAttribute and reloads", () => {
    const delSpy = jest.spyOn(userServiceMock, "deleteUserAttribute");
    const reloadSpy = jest.spyOn(userServiceMock.userAttributesResource, "reload");

    component.deleteCustomAttribute("department");
    expect(delSpy).toHaveBeenCalledWith("department");
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("assignUserToToken opens PIN dialog and assigns user to token, then reloads resources", () => {
    userServiceMock.detailsUsername.set("Alice");
    userServiceMock.selectedUserRealm.set("realm1");

    dialogServiceMock.openDialog = jest.fn().mockReturnValue({
      afterClosed: () => of("1234")
    });
    const reloadUserTokenSpy = jest.spyOn(tokenServiceMock.userTokenResource, "reload");
    const reloadTokenSpy = jest.spyOn(tokenServiceMock.tokenResource, "reload");

    const tokenOption = { serial: "SER-999" } as TokenDetails;
    component.assignUserToToken(tokenOption);

    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    expect(tokenServiceMock.assignUser).toHaveBeenCalledWith({
      tokenSerial: "SER-999",
      username: "Alice",
      realm: "realm1",
      pin: "1234"
    });
    expect(reloadUserTokenSpy).toHaveBeenCalledTimes(1);
    expect(reloadTokenSpy).toHaveBeenCalledTimes(1);
  });

  it("onPageEvent updates service page size/index and opens autocomplete panel", () => {
    const focus = jest.fn();
    component.filterHTMLInputElement = { nativeElement: { focus } } as unknown as ElementRef<HTMLInputElement>;
    const openPanel = jest.fn();
    component.tokenAutoTrigger = { openPanel } as unknown as MatAutocompleteTrigger;

    component.onPageEvent({ pageIndex: 2, pageSize: 25, length: 100 });
    expect(tokenServiceMock.eventPageSize()).toBe(25);
    expect(tokenServiceMock.pageIndex()).toBe(2);

    jest.runOnlyPendingTimers();
    expect(focus).toHaveBeenCalledTimes(1);
    expect(openPanel).toHaveBeenCalledTimes(1);
  });

  it("should not include custom user attributes in detailsEntries", () => {
    userServiceMock.user.set({
      username: "alice",
      givenname: "Alice",
      surname: "Smith",
      email: "alice@example.com",
      custom1: "customValue1",
      custom2: "customValue2",
      editable: false,
      userid: "u123",
      resolver: "default",
      description: "",
      mobile: "",
      phone: ""
    });

    userServiceMock.userAttributesList.set([
      { key: "custom1", value: "customValue1" },
      { key: "custom2", value: "customValue2" }
    ]);

    const entries = component.detailsEntries();
    const keys = entries.map((e) => e.key);

    expect(keys).not.toContain("custom1");
    expect(keys).not.toContain("custom2");
    expect(keys).toContain("username");
    expect(keys).toContain("givenname");
    expect(keys).toContain("surname");
    expect(keys).toContain("email");
    expect(keys).toContain("userid");
    expect(keys).toContain("resolver");
  });

  it("editUser enables inline edit mode with the user data", () => {
    component.userData.set(mockUserData);

    component.editUser();

    expect(component.editMode()).toBe(true);
    expect(component.editedUserData()).toEqual(expect.objectContaining(mockUserData));
  });

  it("should navigateByUrl and reload usersResource on deleteUser success", () => {
    component.userData.set(mockUserData);
    const deleteSpy = jest.spyOn(userServiceMock, "deleteUser").mockReturnValue(of(true));
    const routerSpy = jest.spyOn(component["router"], "navigateByUrl").mockResolvedValue(true);
    userServiceMock.usersResource = { reload: jest.fn() } as unknown as typeof userServiceMock.usersResource;
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({
      afterClosed: () => of(true)
    });

    component.deleteUser();

    expect(deleteSpy).toHaveBeenCalled();
    expect(routerSpy).toHaveBeenCalled();
  });

  describe("inline edit mode", () => {
    beforeEach(() => {
      component.userData.set(mockUserData);
    });

    it("onUpdateEditedUser updates editedUserData", () => {
      component.editUser();
      component.onUpdateEditedUser({ ...mockUserData, email: "new@example.com" });
      expect(component.editedUserData().email).toBe("new@example.com");
    });

    it("editIsDirty is false when not in edit mode even if editedUserData differs", () => {
      component.editedUserData.set({ ...mockUserData, email: "changed@example.com" });
      expect(component.editMode()).toBe(false);
      expect(component.editIsDirty()).toBe(false);
    });

    it("editIsDirty is false right after editUser (snapshot equals current)", () => {
      component.editUser();
      expect(component.editIsDirty()).toBe(false);
    });

    it("editIsDirty becomes true after a field is changed", () => {
      component.editUser();
      component.onUpdateEditedUser({ ...component.editedUserData(), email: "changed@example.com" });
      expect(component.editIsDirty()).toBe(true);
    });

    it("editIsDirty treats null/undefined/empty as equal", () => {
      component.userData.set({ ...mockUserData, description: "" });
      component.editUser();
      component.onUpdateEditedUser({ ...component.editedUserData(), description: undefined });
      expect(component.editIsDirty()).toBe(false);
    });

    it("cancelEdit without changes exits edit mode without opening any dialog", () => {
      component.editUser();
      const openSpy = jest.spyOn(dialogServiceMock, "openDialog");

      component.cancelEdit();

      expect(component.editMode()).toBe(false);
      expect(openSpy).not.toHaveBeenCalled();
    });

    it("cancelEdit with changes and discard exits without saving", () => {
      component.editUser();
      component.onUpdateEditedUser({ ...component.editedUserData(), email: "changed@example.com" });
      dialogServiceMock.openDialog = jest.fn().mockReturnValue({
        afterClosed: () => of("discard")
      });
      const editSpy = jest.spyOn(userServiceMock, "editUser");

      component.cancelEdit();

      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SaveAndExitDialogComponent })
      );
      expect(component.editMode()).toBe(false);
      expect(editSpy).not.toHaveBeenCalled();
    });

    it("cancelEdit with changes and save-exit calls editUser and exits", () => {
      component.editUser();
      component.onUpdateEditedUser({ ...component.editedUserData(), email: "changed@example.com" });
      dialogServiceMock.openDialog = jest.fn().mockReturnValue({
        afterClosed: () => of("save-exit")
      });
      userServiceMock.editUser = jest.fn().mockReturnValue(of(true));
      const reloadSpy = jest.spyOn(userServiceMock.userResource, "reload");

      component.cancelEdit();

      expect(userServiceMock.editUser).toHaveBeenCalledWith(
        mockUserData.resolver,
        expect.objectContaining({ username: mockUserData.username, email: "changed@example.com" })
      );
      expect(reloadSpy).toHaveBeenCalled();
      expect(component.editMode()).toBe(false);
    });

    it("cancelEdit with changes and dialog dismissed stays in edit mode", () => {
      component.editUser();
      component.onUpdateEditedUser({ ...component.editedUserData(), email: "changed@example.com" });
      dialogServiceMock.openDialog = jest.fn().mockReturnValue({
        afterClosed: () => of(undefined)
      });
      const editSpy = jest.spyOn(userServiceMock, "editUser");

      component.cancelEdit();

      expect(component.editMode()).toBe(true);
      expect(editSpy).not.toHaveBeenCalled();
    });

    it("saveEdit forces username from userData even if editedUserData was tampered", () => {
      component.editUser();
      component.editedUserData.set({ ...component.editedUserData(), username: "tampered" });
      userServiceMock.editUser = jest.fn().mockReturnValue(of(true));

      component.saveEdit();

      expect(userServiceMock.editUser).toHaveBeenCalledWith(
        mockUserData.resolver,
        expect.objectContaining({ username: mockUserData.username })
      );
    });

    it("saveEdit stays in edit mode when editUser returns false", () => {
      component.editUser();
      userServiceMock.editUser = jest.fn().mockReturnValue(of(false));
      const reloadSpy = jest.spyOn(userServiceMock.userResource, "reload");

      component.saveEdit();

      expect(component.editMode()).toBe(true);
      expect(reloadSpy).not.toHaveBeenCalled();
    });

    it("pending-changes hasChanges is true when editIsDirty is true", () => {
      const fn = getHasChangesFn();
      component.editUser();
      expect(fn()).toBe(false);

      component.onUpdateEditedUser({ ...component.editedUserData(), email: "changed@example.com" });
      expect(fn()).toBe(true);
    });

    it("pending-changes validChanges is true while in edit mode", () => {
      const fn = getValidChangesFn();
      component.editUser();
      expect(fn()).toBe(true);
    });

    it("pending-changes save dispatches to saveEditAsync when in edit mode", async () => {
      const fn = getSaveFn();
      component.editUser();
      component.onUpdateEditedUser({ ...component.editedUserData(), email: "changed@example.com" });
      userServiceMock.editUser = jest.fn().mockReturnValue(of(true));

      const result = await fn();

      expect(userServiceMock.editUser).toHaveBeenCalled();
      expect(result).toBe(true);
      expect(component.editMode()).toBe(false);
    });

    it("pending-changes save resolves false when editUser fails in edit mode", async () => {
      const fn = getSaveFn();
      component.editUser();
      userServiceMock.editUser = jest.fn().mockReturnValue(of(false));

      const result = await fn();

      expect(result).toBe(false);
      expect(component.editMode()).toBe(true);
    });
  });

  it("should adjust colCount based on breakpoints", () => {
    expect(component.colCount()).toBe(3);

    breakpointSubject.next({ "(max-width: 1000px)": false, "(max-width: 1240px)": true });
    expect(component.colCount()).toBe(2);

    breakpointSubject.next({ "(max-width: 1000px)": true, "(max-width: 1240px)": true });
    expect(component.colCount()).toBe(1);
  });

  it("should split detailsColumns according to colCount", () => {
    userServiceMock.user.set(mockUserData);
    const totalEntries = component.detailsEntries().length;

    expect(component.colCount()).toBe(3);
    let columns = component.detailsColumns();
    expect(columns.length).toBe(3);
    expect(columns.flat().length).toBe(totalEntries);

    breakpointSubject.next({ "(max-width: 1000px)": true, "(max-width: 1240px)": true });
    expect(component.colCount()).toBe(1);
    columns = component.detailsColumns();
    expect(columns.length).toBe(1);
    expect(columns[0].length).toBe(totalEntries);
  });

  describe("pending changes", () => {
    it("registers hasChanges, validChanges, and save in ngOnInit", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("hasChanges reflects attribute input signals", () => {
      const fn = getHasChangesFn();
      expect(fn()).toBe(false);

      component.addKeyInput.set("key");
      expect(fn()).toBe(true);
      component.addKeyInput.set("");

      component.addValueInput.set("value");
      expect(fn()).toBe(true);
      component.addValueInput.set("");

      component.selectedKey.set("k");
      expect(fn()).toBe(true);
    });

    it("validChanges requires both key and value", () => {
      const fn = getValidChangesFn();
      component.keyMode.set("input");
      expect(fn()).toBe(false);

      component.addKeyInput.set("key");
      expect(fn()).toBe(false);

      component.addValueInput.set("value");
      expect(fn()).toBe(true);
    });

    it("save calls setUserAttribute and resolves true on success", async () => {
      component.keyMode.set("input");
      component.addKeyInput.set("key");
      component.addValueInput.set("value");
      const fn = getSaveFn();
      const setSpy = jest.spyOn(userServiceMock, "setUserAttribute");
      const result = await fn();
      expect(setSpy).toHaveBeenCalledWith("key", "value");
      expect(result).toBe(true);
    });

    it("save resolves false when key or value missing", async () => {
      const fn = getSaveFn();
      const setSpy = jest.spyOn(userServiceMock, "setUserAttribute");
      const result = await fn();
      expect(setSpy).not.toHaveBeenCalled();
      expect(result).toBe(false);
    });

    it("ngOnDestroy clears all pending-changes registrations", () => {
      component.ngOnDestroy();
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
    });
  });
});
