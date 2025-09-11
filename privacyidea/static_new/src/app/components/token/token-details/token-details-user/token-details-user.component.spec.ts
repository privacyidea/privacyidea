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
import { TokenDetailsUserComponent } from "./token-details-user.component";
import { Tokens, TokenService } from "../../../../services/token/token.service";
import { signal, WritableSignal } from "@angular/core";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { UserService } from "../../../../services/user/user.service";
import {
  MockAuthService,
  MockLocalService,
  MockNotificationService,
  MockOverflowService,
  MockPiResponse,
  MockRealmService,
  MockTokenService,
  MockUserService
} from "../../../../../testing/mock-services";
import { RealmService } from "../../../../services/realm/realm.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { TokenTypeOption } from "../../token.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

function makeTokenDetailResponse(tokentype: TokenTypeOption): MockPiResponse<Tokens> {
  return {
    id: 0,
    jsonrpc: "2.0",
    signature: "",
    time: Date.now(),
    version: "1.0",
    versionnumber: "1.0",
    detail: {},
    result: {
      status: true,
      value: {
        count: 1,
        current: 1,
        tokens: [
          {
            tokentype,
            active: true,
            revoked: false,
            container_serial: "",
            realms: [],
            count: 0,
            count_window: 0,
            description: "",
            failcount: 0,
            id: 0,
            info: {},
            locked: false,
            maxfail: 0,
            otplen: 0,
            resolver: "",
            rollout_state: "",
            serial: "X",
            sync_window: 0,
            tokengroup: [],
            user_id: "",
            user_realm: "",
            username: ""
          }
        ]
      }
    }
  };
}

describe("TokenDetailsUserComponent", () => {
  let fixture: ComponentFixture<TokenDetailsUserComponent>;
  let component: TokenDetailsUserComponent;

  let tokenSvc: MockTokenService;
  let userSvc: MockUserService;
  let realmSvc: MockRealmService;

  let tokenSerial!: WritableSignal<string>;
  let isEditingUser!: WritableSignal<boolean>;

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [TokenDetailsUserComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: OverflowService, useClass: MockOverflowService },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tokenSvc = TestBed.inject(TokenService) as unknown as MockTokenService;
    userSvc = TestBed.inject(UserService) as unknown as MockUserService;
    realmSvc = TestBed.inject(RealmService) as unknown as MockRealmService;

    fixture = TestBed.createComponent(TokenDetailsUserComponent);
    component = fixture.componentInstance;

    tokenSerial = signal("Mock serial");
    isEditingUser = signal(false);

    component.tokenSerial = tokenSerial;
    component.isEditingUser = isEditingUser;
    component.isEditingInfo = signal(false);
    component.isAnyEditingOrRevoked = signal(false);

    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("tokenType reflects tokenDetailResource tokentype", () => {
    expect(component.tokenType()).toBe("hotp");

    tokenSvc.tokenDetailResource.set(makeTokenDetailResponse("totp"));
    fixture.detectChanges();

    expect(component.tokenType()).toBe("totp");
  });

  it("unassignUser calls service and reloads token details", () => {
    component.unassignUser();

    expect(tokenSvc.unassignUser).toHaveBeenCalledWith("Mock serial");
    expect(tokenSvc.tokenDetailResource.reload).toHaveBeenCalled();
  });

  it("toggleUserEdit flips the flag and reloads default realm", () => {
    expect(isEditingUser()).toBe(false);

    component.toggleUserEdit();

    expect(isEditingUser()).toBe(true);
    expect(realmSvc.defaultRealmResource.reload).toHaveBeenCalled();
  });

  it("cancelUserEdit flips the flag back and clears the selection filter", () => {
    isEditingUser.set(true);

    component.cancelUserEdit();

    expect(isEditingUser()).toBe(false);
    expect(userSvc.selectionFilter()).toBe("");
  });

  it("saveUser assigns user with selectionUsernameFilter + selectedUserRealm and then resets state", () => {
    userSvc.selectionUsernameFilter.set("alice");
    userSvc.selectedUserRealm.set("realmA");

    component.saveUser();

    expect(tokenSvc.assignUser).toHaveBeenCalledWith({
      tokenSerial: "Mock serial",
      username: "alice",
      realm: "realmA"
    });

    expect(userSvc.selectionFilter()).toBe("");
    expect(userSvc.selectedUserRealm()).toBe("");
    expect(tokenSvc.tokenDetailResource.reload).toHaveBeenCalled();
    expect(isEditingUser()).toBe(true);
  });

  it("saveUser works when username is empty string", () => {
    userSvc.selectedUsername.set("");
    userSvc.selectedUserRealm.set("realmB");

    component.saveUser();

    expect(tokenSvc.assignUser).toHaveBeenCalledWith({
      tokenSerial: "Mock serial",
      username: "",
      realm: "realmB"
    });
  });
});
