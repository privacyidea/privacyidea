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
import { BehaviorSubject, map, of } from "rxjs";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

import { UserDetailsComponent } from "./user-details.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BreakpointObserver, BreakpointState } from "@angular/cdk/layout";

import { AuthService } from "../../../services/auth/auth.service";
import { ContentService } from "../../../services/content/content.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { TokenService } from "../../../services/token/token.service";
import { UserService } from "../../../services/user/user.service";
import { MatDialog } from "@angular/material/dialog";
import {
  MockContentService,
  MockDialogService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService
} from "../../../../testing/mock-services";
import { ActivatedRoute } from "@angular/router";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";
import { EditUserDialogComponent } from "@components/user/edit-user-dialog/edit-user-dialog.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { DialogService } from "../../../services/dialog/dialog.service";

class MockMatDialog {
  open = jest.fn().mockReturnValue({
    afterClosed: () => of("1234")
  });
}

describe("UserDetailsComponent", () => {
  let component: UserDetailsComponent;
  let fixture: ComponentFixture<UserDetailsComponent>;

  let userServiceMock: MockUserService;
  let tokenServiceMock: MockTokenService;
  let dialogServiceMock: MockDialogService;
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
      imports: [UserDetailsComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: BreakpointObserver,
          useValue: {
            observe: (query: string) => breakpointSubject.pipe(map((b) => ({ matches: b[query] || false, breakpoints: {} })))
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
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: DialogService, useClass: MockDialogService },
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

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("tokenDataSource populates from tokenResource and keeps previous when resource is missing", () => {
    tokenServiceMock.tokenResourceValue.set({
      count: 2,
      current: 2,
      tokens: [
        { serial: "T-1", revoked: false, locked: false } as any,
        { serial: "T-2", revoked: false, locked: false } as any
      ]
    });
    fixture.detectChanges();

    expect(component.tokenDataSource().data.map((t) => t.serial)).toEqual(["T-1", "T-2"]);
    expect(component.total()).toBe(2);

    tokenServiceMock.tokenResource.value.set(undefined as any);
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

  it("addCustomAttribute calls setUserAttribute and reloads userAttributesResource, then clears inputs", () => {
    userServiceMock.attributeSetMap.set({
      department: ["sales", "finance"],
      customKey: ["2", "1"]
    });
    component.keyMode.set("select");
    component.selectedKey.set("department");
    component.selectedValue.set("sales");

    const setSpy = jest.spyOn(userServiceMock, "setUserAttribute");
    const reloadSpy = jest.spyOn(userServiceMock.userAttributesResource, "reload");

    component.addCustomAttribute();
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

    const tokenOption = { serial: "SER-999" } as any;
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

  it("onPageEvent updates service page size/index and opens autocomplete panel", async () => {
    const focus = jest.fn();
    (component as any).filterHTMLInputElement = { nativeElement: { focus } };
    const openPanel = jest.fn();
    (component as any).tokenAutoTrigger = { openPanel };

    component.onPageEvent({ pageIndex: 2, pageSize: 25, length: 100 } as any);
    expect(tokenServiceMock.eventPageSize).toBe(25);
    expect(tokenServiceMock.pageIndex()).toBe(2);

    jest.runOnlyPendingTimers();
    expect(focus).toHaveBeenCalledTimes(1);
    expect(openPanel).toHaveBeenCalledTimes(1);
  });

  it("should not include custom user attributes in detailsEntries", () => {
    // Setup user data with standard and custom keys

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

    // Setup custom attributes list
    userServiceMock.userAttributesList.set([
      { key: "custom1", value: "customValue1" },
      { key: "custom2", value: "customValue2" }
    ]);

    // detailsEntries should not include custom1 or custom2
    const entries = component.detailsEntries();
    const keys = entries.map((e) => e.key);

    expect(keys).not.toContain("custom1");
    expect(keys).not.toContain("custom2");
    // Should contain standard keys
    expect(keys).toContain("username");
    expect(keys).toContain("givenname");
    expect(keys).toContain("surname");
    expect(keys).toContain("email");
    expect(keys).toContain("userid");
    expect(keys).toContain("resolver");
  });

  it("editUser opens EditUserDialogComponent with user data", () => {
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({
      afterClosed: () => of(true)
    });
    component.userData.set(mockUserData);

    component.editUser();

    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: EditUserDialogComponent,
      data: expect.objectContaining(mockUserData)
    });
  });

  it("should navigateByUrl and reload usersResource on deleteUser success", () => {
    component.userData.set(mockUserData);
    const deleteSpy = jest.spyOn(userServiceMock, "deleteUser").mockReturnValue(of(true));
    const routerSpy = jest.spyOn((component as any).router, "navigateByUrl").mockResolvedValue(true);
    userServiceMock.usersResource = { reload: jest.fn() } as any;
    dialogServiceMock.openDialog = jest.fn().mockReturnValue({
      afterClosed: () => of(true)
    });

    component.deleteUser();

    expect(deleteSpy).toHaveBeenCalled();
    expect(routerSpy).toHaveBeenCalled();
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

    // Default 3 columns
    expect(component.colCount()).toBe(3);
    let columns = component.detailsColumns();
    expect(columns.length).toBe(3);
    expect(columns.flat().length).toBe(totalEntries);

    // 1 column
    breakpointSubject.next({ "(max-width: 1000px)": true, "(max-width: 1240px)": true });
    expect(component.colCount()).toBe(1);
    columns = component.detailsColumns();
    expect(columns.length).toBe(1);
    expect(columns[0].length).toBe(totalEntries);
  });
});
