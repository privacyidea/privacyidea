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
import { WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { of, throwError } from "rxjs";
import { UserDetailsLockDialogComponent } from "./user-details-lock-dialog/user-details-lock-dialog.component";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { CUSTOM_KEY_OPTION, UserDetailsComponent } from "./user-details.component";

import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute } from "@angular/router";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { AuditService } from "@services/audit/audit.service";
import { AuthService } from "@services/auth/auth.service";
import { AuthenticationLogService } from "@services/authentication-log/authentication-log.service";
import { ConditionalAccessStateService } from "@services/conditional-access-state/conditional-access-state.service";
import { ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenDetails, TokenService } from "@services/token/token.service";
import { UserData, UserService } from "@services/user/user.service";
import {
  MockAuditService,
  MockAuthenticationLogService,
  MockConditionalAccessStateService,
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
  let notificationServiceMock: MockNotificationService;
  let dialogMock: MockMatDialog;
  let authenticationLogServiceMock: MockAuthenticationLogService;
  let authServiceMock: MockAuthService;
  let conditionalAccessStateServiceMock: MockConditionalAccessStateService;

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

    await TestBed.configureTestingModule({
      imports: [UserDetailsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: UserService, useClass: MockUserService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: AuditService, useClass: MockAuditService },
        { provide: AuthenticationLogService, useClass: MockAuthenticationLogService },
        { provide: ConditionalAccessStateService, useClass: MockConditionalAccessStateService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: MatDialog, useValue: dialogMock },
        MockLocalService
      ]
    }).compileComponents();
    jest.useFakeTimers();

    fixture = TestBed.createComponent(UserDetailsComponent);
    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    authenticationLogServiceMock = TestBed.inject(AuthenticationLogService) as unknown as MockAuthenticationLogService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    conditionalAccessStateServiceMock = TestBed.inject(
      ConditionalAccessStateService
    ) as unknown as MockConditionalAccessStateService;

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

    tokenServiceMock.tokenResource.value.set(undefined);
    fixture.detectChanges();

    expect(component.tokenDataSource().data.map((t) => t.serial)).toEqual(["T-1", "T-2"]);
  });

  const setRow = (values: Partial<ReturnType<typeof component.attributeRow>>) =>
    component.attributeRow.update((row) => ({ ...row, ...values }));

  it("switches key mode between input/select as expected", () => {
    expect(component.keyMode()).toBe("select");

    setRow({ selectedKey: "department" });
    component.switchToCustomKey();
    expect(component.keyMode()).toBe("input");
    expect(component.attributeRow().selectedKey).toBe("");

    setRow({ customKey: "typed" });
    component.switchToSelectKey();
    expect(component.keyMode()).toBe("select");
    expect(component.attributeRow().customKey).toBe("");
  });

  it("switches to the free-text key when the custom option is chosen", () => {
    setRow({ selectedKey: CUSTOM_KEY_OPTION });
    fixture.detectChanges();
    expect(component.keyMode()).toBe("input");
    expect(component.attributeRow().selectedKey).toBe("");
  });

  it("valueOptions / isValueInput / canAddAttribute computed helpers", () => {
    userServiceMock.attributeSetMap.set({
      department: ["sales", "finance"],
      customKey: ["2", "1"]
    });
    setRow({ selectedKey: "department" });
    expect(component.valueOptions()).toEqual(["sales", "finance"]);
    expect(component.isValueInput()).toBe(false);

    setRow({ selectedValue: "sales" });
    expect(component.canAddAttribute()).toBe(true);

    component.switchToCustomKey();
    setRow({ customKey: "customKey" });
    expect(component.valueOptions()).toEqual(["2", "1"]);
    expect(component.isValueInput()).toBe(false);

    setRow({ selectedValue: "" });
    expect(component.canAddAttribute()).toBe(false);
    setRow({ selectedValue: "foo" });
    expect(component.canAddAttribute()).toBe(true);
  });

  it("canAddAttribute reads the key and value rules of the active input mode only", () => {
    setRow({ customValue: "free" });
    expect(component.isValueInput()).toBe(true);
    expect(component.canAddAttribute()).toBe(false);

    setRow({ selectedKey: "department" });
    expect(component.canAddAttribute()).toBe(true);

    setRow({ selectedKey: "   " });
    expect(
      component.attributeForm
        .selectedKey()
        .errors()
        .map((e) => e.kind)
    ).toEqual(["required"]);
    expect(component.canAddAttribute()).toBe(false);

    component.switchToCustomKey();
    setRow({ customKey: "key", customValue: "  " });
    expect(
      component.attributeForm
        .customValue()
        .errors()
        .map((e) => e.kind)
    ).toEqual(["required"]);
    expect(component.canAddAttribute()).toBe(false);

    setRow({ customValue: "value" });
    expect(component.canAddAttribute()).toBe(true);
    expect(component.attributeKey()).toBe("key");
    expect(component.attributeValue()).toBe("value");
  });

  it("addCustomAttribute calls setUserAttribute and reloads userAttributesResource, then clears inputs", async () => {
    userServiceMock.attributeSetMap.set({
      department: ["sales", "finance"],
      customKey: ["2", "1"]
    });
    setRow({ selectedKey: "department", selectedValue: "sales" });
    component.attributeForm.selectedKey().markAsDirty();

    const setSpy = jest.spyOn(userServiceMock, "setUserAttribute");
    const reloadSpy = jest.spyOn(userServiceMock.userAttributesResource, "reload");

    const result = await component.addCustomAttribute();
    expect(result).toBe(true);
    expect(setSpy).toHaveBeenCalledWith("department", "sales");
    expect(reloadSpy).toHaveBeenCalledTimes(1);

    expect(component.attributeRow()).toEqual({
      keyMode: "select",
      selectedKey: "",
      customKey: "",
      selectedValue: "",
      customValue: ""
    });
    expect(component.attributeForm().dirty()).toBe(false);
  });

  it("addCustomAttribute keeps the row and resolves false when the request fails", async () => {
    setRow({ selectedKey: "department", selectedValue: "sales" });
    jest.spyOn(userServiceMock, "setUserAttribute").mockReturnValue(throwError(() => new Error("boom")));

    expect(await component.addCustomAttribute()).toBe(false);
    expect(component.attributeRow().selectedKey).toBe("department");
  });

  describe("add-attribute row template", () => {
    const keyOptionsSignal = () => userServiceMock.keyOptions as WritableSignal<string[]>;
    const wildcardSignal = () => userServiceMock.hasWildcardKey as WritableSignal<boolean>;
    const inputs = (): HTMLInputElement[] => Array.from(fixture.nativeElement.querySelectorAll(".add-attr-row input"));
    const saveButton = (): HTMLButtonElement => fixture.nativeElement.querySelector(".add-attr-row button[color]");
    const type = (input: HTMLInputElement, value: string) => {
      input.value = value;
      input.dispatchEvent(new Event("input"));
      fixture.detectChanges();
    };
    const pick = (selectIndex: number, optionIndex: number) => {
      const select = fixture.debugElement.queryAll(By.directive(MatSelect))[selectIndex].componentInstance as MatSelect;
      select.open();
      fixture.detectChanges();
      select.options.get(optionIndex)?._getHostElement().click();
      fixture.detectChanges();
    };

    beforeEach(() => {
      keyOptionsSignal().set(["department", "title"]);
      wildcardSignal().set(true);
      userServiceMock.attributeSetMap.set({ department: ["sales", "finance"], "*": ["*"] });
      fixture.detectChanges();
    });

    it("writes the selected key and value into the row and enables the save button", () => {
      expect(saveButton().disabled).toBe(true);
      pick(0, 0);
      expect(component.attributeRow().selectedKey).toBe("department");
      expect(fixture.debugElement.queryAll(By.directive(MatSelect))).toHaveLength(2);
      pick(1, 1);
      expect(component.attributeRow().selectedValue).toBe("finance");
      expect(component.attributeForm().dirty()).toBe(true);
      expect(getHasChangesFn()()).toBe(true);
      expect(saveButton().disabled).toBe(false);
    });

    it("switches to a free-text key through the custom option and back through the arrow button", () => {
      pick(0, 2);
      expect(component.keyMode()).toBe("input");
      expect(component.attributeRow().selectedKey).toBe("");
      expect(inputs()).toHaveLength(2);

      type(inputs()[0], "nickname");
      expect(component.attributeRow().customKey).toBe("nickname");
      expect(component.attributeKey()).toBe("nickname");

      (fixture.nativeElement.querySelector(".return-button") as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(component.keyMode()).toBe("select");
      expect(component.attributeRow().customKey).toBe("");
      expect(fixture.debugElement.queryAll(By.directive(MatSelect))).toHaveLength(1);
    });

    it("writes typed key and value into the row and keeps the save button disabled while one is blank", () => {
      pick(0, 2);
      type(inputs()[0], "nickname");
      expect(saveButton().disabled).toBe(true);
      type(inputs()[1], "   ");
      expect(saveButton().disabled).toBe(true);
      type(inputs()[1], "ally");
      expect(component.attributeRow().customValue).toBe("ally");
      expect(saveButton().disabled).toBe(false);
    });

    it("saves the typed attribute through the button and resets the row", async () => {
      pick(0, 2);
      type(inputs()[0], " nickname ");
      type(inputs()[1], " ally ");
      const setSpy = jest.spyOn(userServiceMock, "setUserAttribute");
      saveButton().click();
      await Promise.resolve();
      fixture.detectChanges();
      expect(setSpy).toHaveBeenCalledWith("nickname", "ally");
      expect(component.attributeRow().customKey).toBe("");
      expect(component.attributeRow().keyMode).toBe("input");
      expect(component.attributeForm().dirty()).toBe(false);
      expect(component.attributeForm().touched()).toBe(false);
    });
  });

  it("deleteCustomAttribute calls deleteUserAttribute and reloads", () => {
    const delSpy = jest.spyOn(userServiceMock, "deleteUserAttribute");
    const reloadSpy = jest.spyOn(userServiceMock.userAttributesResource, "reload");

    component.deleteCustomAttribute("department");
    expect(delSpy).toHaveBeenCalledWith("department");
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("showUserAuditLog filters the audit log for exactly the current user and realm", () => {
    const auditServiceMock = TestBed.inject(AuditService) as unknown as MockAuditService;
    userServiceMock.detailsUser.set({ username: "Alice", realm: "realm1" });

    component.showUserAuditLog();

    expect(auditServiceMock.activeFilter().value).toBe("user: =Alice realm: =realm1");
  });

  it("showUserAuditLog leaves the realm out when the user has none", () => {
    const auditServiceMock = TestBed.inject(AuditService) as unknown as MockAuditService;
    userServiceMock.detailsUser.set({ username: "Alice", realm: "" });

    component.showUserAuditLog();

    expect(auditServiceMock.activeFilter().value).toBe("user: =Alice");
  });

  it("showUserAuthenticationLog sets username and realm filter for the current user", () => {
    userServiceMock.detailsUser.set({ username: "Alice", realm: "realm1" });

    component.showUserAuthenticationLog();

    expect(authenticationLogServiceMock.authenticationLogFilter().getValueOfKey("username")).toBe("Alice");
    expect(authenticationLogServiceMock.authenticationLogFilter().getValueOfKey("realm")).toBe("realm1");
  });

  it("shows the auth-log header link only when authentication_log_read is allowed", () => {
    expect(fixture.nativeElement.querySelector(".details-header mat-icon.mdi--list-lock")).toBeNull();

    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["authentication_log_read"]
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".details-header mat-icon.mdi--list-lock")).not.toBeNull();
  });

  it("assignUserToToken opens PIN dialog and assigns user to token, then reloads resources", () => {
    userServiceMock.detailsUser.set({ username: "Alice", realm: "realm1" });
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

  it("enrollNewToken navigates to token enrollment with the user as query parameters", () => {
    userServiceMock.detailsUser.set({ username: "Alice", realm: "realm1" });
    const navigateSpy = jest.spyOn(component["router"], "navigate").mockResolvedValue(true);

    component.enrollNewToken();

    expect(navigateSpy).toHaveBeenCalledWith([ROUTE_PATHS.TOKENS_ENROLLMENT], {
      queryParams: { realm: "realm1", user: "Alice" }
    });
  });

  it("createNewContainer navigates to container create with the user as query parameters", () => {
    userServiceMock.detailsUser.set({ username: "Alice", realm: "realm1" });
    const navigateSpy = jest.spyOn(component["router"], "navigate").mockResolvedValue(true);

    component.createNewContainer();

    expect(navigateSpy).toHaveBeenCalledWith([ROUTE_PATHS.CONTAINERS_CREATE], {
      queryParams: { realm: "realm1", user: "Alice" }
    });
  });

  it("detailsEntries lists the user data attributes and excludes the editable flag", () => {
    userServiceMock.user.set({
      username: "alice",
      givenname: "Alice",
      surname: "Smith",
      email: "alice@example.com",
      editable: false,
      userid: "u123",
      resolver: "default",
      description: "",
      mobile: "",
      phone: ""
    });

    const entries = component.detailsEntries();
    const keys = entries.map((e) => e.key);

    expect(keys).not.toContain("editable");
    expect(keys).toContain("username");
    expect(keys).toContain("givenname");
    expect(keys).toContain("surname");
    expect(keys).toContain("email");
    expect(keys).toContain("userid");
    expect(keys).toContain("resolver");
  });

  it("detailsEntries falls back to the raw key label and dash placeholder for unmapped or nullish attributes", () => {
    userServiceMock.user.set({
      ...mockUserData,
      groups: undefined
    });

    const entries = component.detailsEntries();
    const groupsEntry = entries.find((e) => e.key === "groups");

    expect(groupsEntry?.label).toBe("groups");
    expect(groupsEntry?.value).toBe("-");
  });

  it("detailsEntries returns an empty list when userData is not set", () => {
    userServiceMock.user.set(undefined as unknown as UserData);

    expect(component.detailsEntries()).toEqual([]);
  });

  it("str stringifies values and normalizes null/undefined to an empty string", () => {
    expect(component["str"](null)).toBe("");
    expect(component["str"](undefined)).toBe("");
    expect(component["str"](0)).toBe("0");
    expect(component["str"]("abc")).toBe("abc");
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

    it("editIsDirty falls back to an empty object when userData is missing", () => {
      component.editMode.set(true);
      component.editedUserData.set({ username: "alice" });
      component.userData.set(undefined as unknown as typeof mockUserData);

      expect(component.editIsDirty()).toBe(true);
    });

    it("editIsDirty treats keys missing from the original user data as empty strings", () => {
      component.editUser();
      component.editedUserData.set({ ...component.editedUserData(), extraField: "new-value" });

      expect(component.editIsDirty()).toBe(true);
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

    it("cancelEdit with changes and save-exit calls editUser and exits", async () => {
      component.editUser();
      component.onUpdateEditedUser({ ...component.editedUserData(), email: "changed@example.com" });
      dialogServiceMock.openDialog = jest.fn().mockReturnValue({
        afterClosed: () => of("save-exit")
      });
      userServiceMock.editUser = jest.fn().mockReturnValue(of(true));
      const reloadSpy = jest.spyOn(userServiceMock.userResource, "reload");

      component.cancelEdit();
      await Promise.resolve();

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

    it("pending-changes save logs and shows a notification when editUser throws an Error", async () => {
      const errorSpy = jest.spyOn(console, "error").mockImplementation();
      const fn = getSaveFn();
      component.editUser();
      userServiceMock.editUser = jest.fn().mockReturnValue(throwError(() => new Error("network down")));

      const result = await fn();

      expect(errorSpy).toHaveBeenCalledWith("Failed to save user edits", expect.any(Error));
      expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to save user edits. network down");
      expect(result).toBe(false);
      expect(component.editMode()).toBe(true);
    });

    it("pending-changes save shows a stringified notification when editUser throws a non-Error value", async () => {
      const fn = getSaveFn();
      component.editUser();
      userServiceMock.editUser = jest.fn().mockReturnValue(throwError(() => "boom"));

      const result = await fn();

      expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to save user edits. boom");
      expect(result).toBe(false);
      expect(component.editMode()).toBe(true);
    });
  });

  it("toggleExpanded flips expansion state per key", () => {
    expect(component.isExpanded("groups")).toBe(false);

    component.toggleExpanded("groups");
    expect(component.isExpanded("groups")).toBe(true);
    expect(component.isExpanded("other")).toBe(false);

    component.toggleExpanded("other");
    expect(component.isExpanded("groups")).toBe(true);
    expect(component.isExpanded("other")).toBe(true);

    component.toggleExpanded("groups");
    expect(component.isExpanded("groups")).toBe(false);
    expect(component.isExpanded("other")).toBe(true);
  });

  describe("pending changes", () => {
    it("registers hasChanges, validChanges, and save in ngOnInit", () => {
      expect(pendingChangesService.registerHasChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerValidChanges).toHaveBeenCalled();
      expect(pendingChangesService.registerSave).toHaveBeenCalled();
    });

    it("hasChanges reflects attribute row inputs", () => {
      const fn = getHasChangesFn();
      expect(fn()).toBe(false);

      setRow({ customKey: "key" });
      expect(fn()).toBe(true);
      setRow({ customKey: "" });

      setRow({ customValue: "value" });
      expect(fn()).toBe(true);
      setRow({ customValue: "" });

      setRow({ selectedValue: "v" });
      expect(fn()).toBe(true);
      setRow({ selectedValue: "" });

      setRow({ selectedKey: "k" });
      expect(fn()).toBe(true);
    });

    it("validChanges requires both key and value", () => {
      const fn = getValidChangesFn();
      component.switchToCustomKey();
      expect(fn()).toBe(false);

      setRow({ customKey: "key" });
      expect(fn()).toBe(false);

      setRow({ customValue: "value" });
      expect(fn()).toBe(true);
    });

    it("validChanges is true while editing the user", () => {
      component.editMode.set(true);
      expect(getValidChangesFn()()).toBe(true);
    });

    it("save calls setUserAttribute and resolves true on success", async () => {
      component.switchToCustomKey();
      setRow({ customKey: "key", customValue: "value" });
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

  it("shows lock state card with 'Unlocked' status when user_lock_read is allowed", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["user_lock_read"]
    });
    conditionalAccessStateServiceMock.setUserLockStatus(null);

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain("User Lock");
    expect(fixture.nativeElement.textContent).toContain("Unlocked");
  });

  it("shows reset lock action for locked users and triggers reset + reload after confirmation", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["user_lock_read", "user_lock_reset"]
    });
    conditionalAccessStateServiceMock.setUserLockStatus({
      resolver: "resolver1",
      uid: "uid-123",
      realm: "realm1",
      username: "Alice",
      permanent: false,
      lock_expires_at: "2030-01-01T10:00:00Z",
      seconds_remaining: 120,
      user_role: "user",
      lock_cause: "POLICY",
      locked_at: "2030-01-01T09:58:00Z",
      error_message: null
    });
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({
      afterClosed: () => of(true)
    });

    const reloadSpy = jest.spyOn(conditionalAccessStateServiceMock.userLockResource, "reload");

    fixture.detectChanges();
    component.resetUserLock();

    expect(conditionalAccessStateServiceMock.resetUserLock).toHaveBeenCalledWith({
      resolver: "resolver1",
      uid: "uid-123",
      realm: "realm1"
    });
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("lockStatusText reports a permanent lock", () => {
    conditionalAccessStateServiceMock.setUserLockStatus({
      resolver: "resolver1",
      uid: "uid-123",
      realm: "realm1",
      username: "Alice",
      permanent: true,
      lock_expires_at: null,
      seconds_remaining: null,
      user_role: "user",
      lock_cause: "POLICY",
      locked_at: "2030-01-01T09:58:00Z",
      error_message: null
    });
    expect(component.lockStatusText()).toBe("Locked permanently");
  });

  it("lockStatusText falls back to 'Locked' when locked without an expiry", () => {
    conditionalAccessStateServiceMock.setUserLockStatus({
      resolver: "resolver1",
      uid: "uid-123",
      realm: "realm1",
      username: "Alice",
      permanent: false,
      lock_expires_at: null,
      seconds_remaining: null,
      user_role: "user",
      lock_cause: "POLICY",
      locked_at: "2030-01-01T09:58:00Z",
      error_message: null
    });
    expect(component.lockStatusText()).toBe("Locked");
  });

  it("resetUserLock does nothing when the user is not locked", () => {
    conditionalAccessStateServiceMock.setUserLockStatus(null);
    dialogServiceMock.openDialog = jest.fn();

    component.resetUserLock();

    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
    expect(conditionalAccessStateServiceMock.resetUserLock).not.toHaveBeenCalled();
  });

  it("resetUserLock reports when nothing was reset (already gone or out of scope)", () => {
    conditionalAccessStateServiceMock.setUserLockStatus({
      resolver: "resolver1",
      uid: "uid-123",
      realm: "realm1",
      username: "Alice",
      permanent: false,
      lock_expires_at: "2030-01-01T10:00:00Z",
      seconds_remaining: 120,
      user_role: "user",
      lock_cause: "POLICY",
      locked_at: "2030-01-01T09:58:00Z",
      error_message: null
    });
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({ afterClosed: () => of(true) });
    (conditionalAccessStateServiceMock.resetUserLock as jest.Mock).mockReturnValue(of(false));

    component.resetUserLock();

    expect(notificationServiceMock.error).toHaveBeenCalled();
  });

  it("lockUser opens the dialog and locks with the chosen duration", () => {
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({
      afterClosed: () => of({ durationSeconds: 600 })
    });
    const reloadSpy = jest.spyOn(conditionalAccessStateServiceMock.userLockResource, "reload");

    component.lockUser();

    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({ component: UserDetailsLockDialogComponent })
    );
    expect(conditionalAccessStateServiceMock.setUserLock).toHaveBeenCalledWith(
      expect.objectContaining({ duration_seconds: 600 })
    );
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it("lockUser omits the duration for a permanent lock", () => {
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({
      afterClosed: () => of({ durationSeconds: null })
    });

    component.lockUser();

    expect(conditionalAccessStateServiceMock.setUserLock).toHaveBeenCalledWith(
      expect.objectContaining({ duration_seconds: undefined })
    );
  });

  it("lockUser does nothing when the dialog is cancelled", () => {
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({ afterClosed: () => of(null) });

    component.lockUser();

    expect(conditionalAccessStateServiceMock.setUserLock).not.toHaveBeenCalled();
  });

  it("hides the lock action without user_lock_set", () => {
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["user_lock_read"]
    });
    conditionalAccessStateServiceMock.setUserLockStatus(null);

    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector(".user-lock-actions button")).toBeNull();
  });

  it("names who imposed the lock now in force", () => {
    conditionalAccessStateServiceMock.setUserLockStatus({
      resolver: "resolver1",
      uid: "uid-123",
      realm: "realm1",
      username: "Alice",
      permanent: true,
      lock_expires_at: null,
      seconds_remaining: null,
      user_role: "user",
      lock_cause: "MANUAL",
      locked_at: "2030-01-01T09:58:00Z",
      error_message: null
    });
    expect(component.lockCauseLabel()).toBe("Locked by an administrator");
  });

  it("resetUserLock does not reset when the confirmation is cancelled", () => {
    conditionalAccessStateServiceMock.setUserLockStatus({
      resolver: "resolver1",
      uid: "uid-123",
      realm: "realm1",
      username: "Alice",
      permanent: false,
      lock_expires_at: "2030-01-01T10:00:00Z",
      seconds_remaining: 120,
      user_role: "user",
      lock_cause: "POLICY",
      locked_at: "2030-01-01T09:58:00Z",
      error_message: null
    });
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({ afterClosed: () => of(false) });

    component.resetUserLock();

    expect(conditionalAccessStateServiceMock.resetUserLock).not.toHaveBeenCalled();
  });
});
