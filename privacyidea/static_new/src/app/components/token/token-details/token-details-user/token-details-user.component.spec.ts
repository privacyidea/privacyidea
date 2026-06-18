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
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EditableElement } from "@components/shared/edit-buttons/edit-buttons.component";
import { AuthService } from "@services/auth/auth.service";
import { NotificationService } from "@services/notification/notification.service";
import { RealmService } from "@services/realm/realm.service";
import { Tokens, TokenService, TokenTypeKey } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import {
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockPiResponse,
  MockRealmService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { TokenDetailsUserComponent } from "./token-details-user.component";
import { TokenDetailsUserSelfServiceComponent } from "./token-details-user.self-service.component";
import { ContentService } from "@services/content/content.service";

function makeTokenDetailResponse(tokentype: TokenTypeKey): MockPiResponse<Tokens> {
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
  let tokenService: MockTokenService;
  let userService: MockUserService;
  let realmService: MockRealmService;

  let tokenSerial!: WritableSignal<string>;
  let isEditingUser!: WritableSignal<boolean>;

  beforeEach(async () => {
    jest.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [TokenDetailsUserComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: UserService, useClass: MockUserService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;

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

    tokenService.tokenDetailResource.set(makeTokenDetailResponse("totp"));
    fixture.detectChanges();

    expect(component.tokenType()).toBe("totp");
  });

  it("unassignUser calls service and reloads token details", () => {
    component.unassignUser();

    expect(tokenService.unassignUser).toHaveBeenCalledWith("Mock serial");
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
  });

  it("toggleUserEdit flips the flag and reloads default realm", () => {
    expect(isEditingUser()).toBe(false);

    component.toggleUserEdit();

    expect(isEditingUser()).toBe(true);
    expect(realmService.defaultRealmResource.reload).toHaveBeenCalled();
  });

  it("cancelUserEdit flips the flag back and clears the selection filter", () => {
    isEditingUser.set(true);

    component.cancelUserEdit();

    expect(isEditingUser()).toBe(false);
    expect(userService.selectionFilter()).toBe("");
  });

  it("saveUser assigns user with selectionUsernameFilter + selectedUserRealm and then resets state", () => {
    userService.selectionUsernameFilter.set("alice");
    userService.selectedUserRealm.set("realmA");

    component.saveUser();

    expect(tokenService.assignUser).toHaveBeenCalledWith({
      tokenSerial: "Mock serial",
      username: "alice",
      realm: "realmA"
    });

    expect(userService.selectionFilter()).toBe("");
    expect(userService.selectedUserRealm()).toBe("");
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
    expect(isEditingUser()).toBe(true);
  });

  it("assignToSelf assigns the logged-in user and reloads token details", () => {
    component.assignToSelf();

    expect(tokenService.assignUser).toHaveBeenCalledWith({
      tokenSerial: "Mock serial",
      username: "alice",
      realm: "default"
    });
    expect(tokenService.tokenDetailResource.reload).toHaveBeenCalled();
  });

  it("renders the username as a link in the admin component but as plain text in the self-service component", () => {
    const row: EditableElement = { keyMap: { key: "username" }, value: "alice", isEditing: signal(false) };
    isEditingUser.set(false);

    component.userData.set([row]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector("a")).toBeTruthy();

    const ssFixture = TestBed.createComponent(TokenDetailsUserSelfServiceComponent);
    ssFixture.componentInstance.userData.set([row]);
    ssFixture.componentInstance.isAnyEditingOrRevoked = signal(false);
    ssFixture.detectChanges();
    expect(ssFixture.nativeElement.querySelector("a")).toBeNull();
  });

  it("offers only unassign when a user is already assigned", () => {
    const auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    auth.role.set("user");
    auth.actionAllowed.mockImplementation((action: string) => action === "assign" || action === "unassign");
    component.userData.set([{ keyMap: { key: "username" }, value: "daemon", isEditing: signal(false) }]);
    isEditingUser.set(false);
    fixture.detectChanges();

    const icons = Array.from(fixture.nativeElement.querySelectorAll("mat-icon")).map((e: Element) =>
      e.textContent?.trim()
    );
    expect(icons).toContain("person_remove");
    expect(icons).not.toContain("person_add");
  });
});
