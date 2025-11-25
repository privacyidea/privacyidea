/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { of } from "rxjs";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

import { UserDetailsComponent } from "./user-details.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

import { AuthService } from "../../../services/auth/auth.service";
import { ContentService } from "../../../services/content/content.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { TokenService } from "../../../services/token/token.service";
import { UserService } from "../../../services/user/user.service";
import { MatDialog } from "@angular/material/dialog";
import {
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService
} from "../../../../testing/mock-services";
import { ActivatedRoute } from "@angular/router";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

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
  let dialogMock: MockMatDialog;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    dialogMock = new MockMatDialog();

    await TestBed.configureTestingModule({
      imports: [UserDetailsComponent, BrowserAnimationsModule],
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
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: MatDialog, useValue: dialogMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();
    jest.useFakeTimers();

    fixture = TestBed.createComponent(UserDetailsComponent);
    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;

    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("tokenDataSource populates from tokenResource and keeps previous when resource is missing", () => {
    tokenServiceMock.tokenResource.value.set({
      detail: {},
      id: 0,
      jsonrpc: "2.0",
      signature: "",
      time: Date.now(),
      version: "1.0",
      versionnumber: "1.0",
      result: {
        status: true,
        value: {
          count: 2,
          current: 2,
          tokens: [
            { serial: "T-1", revoked: false, locked: false } as any,
            { serial: "T-2", revoked: false, locked: false } as any
          ]
        }
      }
    } as any);
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

    const reloadUserTokenSpy = jest.spyOn(tokenServiceMock.userTokenResource, "reload");
    const reloadTokenSpy = jest.spyOn(tokenServiceMock.tokenResource, "reload");

    const tokenOption = { serial: "SER-999" } as any;
    component.assignUserToToken(tokenOption);

    expect(dialogMock.open).toHaveBeenCalled();
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
});
