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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { RealmService } from "@services/realm/realm.service";
import { TokenDetails, Tokens, TokenService } from "@services/token/token.service";
import { EditUserData, UserAttributePolicy, UserData, UserService } from "./user.service";

import { signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { NotificationService } from "@services/notification/notification.service";
import {
  MockContentService,
  MockHttpResourceRef,
  MockLocalService,
  MockNotificationService,
  MockPiResponse,
  MockRealmService,
  MockTokenService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";

function buildUser(username: string): UserData {
  return {
    username,
    userid: username,
    description: "",
    editable: true,
    email: `${username}@test`,
    givenname: username,
    surname: "Tester",
    mobile: "",
    phone: "",
    resolver: ""
  };
}

function setTokenDetailUsername(name: string) {
  const ref = (TestBed.inject(TokenService) as unknown as MockTokenService).tokenDetailResource;

  if (!ref.value()) {
    const seeded = MockPiResponse.fromValue<Tokens>({
      tokens: [{ username: name } as Partial<TokenDetails> as TokenDetails]
    } as Partial<Tokens> as Tokens) as unknown as PiResponse<Tokens>;
    ref.set(seeded);
    return;
  }

  ref.update((resp) => {
    const current = resp!.result!.value as unknown as Tokens;
    const first = (current.tokens?.[0] ?? ({} as Partial<TokenDetails> as TokenDetails));
    first.username = name;
    return {
      ...resp!,
      result: {
        ...resp!.result!,
        value: { ...current, tokens: [first] }
      }
    } as PiResponse<Tokens>;
  });
}

describe("UserService", () => {
  let userService: UserService;
  let realmService: MockRealmService;
  let httpMock: HttpTestingController;
  let contentServiceMock: MockContentService;
  let authServiceMock: MockAuthService;
  let notificationServiceMock: MockNotificationService;

  let users: UserData[];
  let alice: UserData;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        UserService,
        { provide: RealmService, useClass: MockRealmService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService },
        MockLocalService
      ]
    });

    userService = TestBed.inject(UserService);
    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    httpMock = TestBed.inject(HttpTestingController);
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    alice = buildUser("Alice");
    users = [alice, buildUser("Bob"), buildUser("Charlie")];
    userService.users.set(users);
    userService.detailsUser.set({ username: "Alice", realm: "" });
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(userService).toBeTruthy();
  });

  it("selectedUserRealm should expose the current defaultRealm", () => {
    realmService.realmOptions.set(["realm1", "realm2", "someRealm"]);
    expect(userService.selectedUserRealm()).toBe("realm1");
    realmService.setDefaultRealm("someRealm");
    expect(userService.selectedUserRealm()).toBe("someRealm");
  });

  it("selectedUserRealm should expose first realm if no default realm is set", () => {
    realmService.realmOptions.set(["realm1", "realm2"]);
    expect(userService.selectedUserRealm()).toBe("realm1");
  });

  it("selectedUserRealm should expose empty string if no realmOptions are available", () => {
    realmService.realmOptions.set([]);
    expect(userService.selectedUserRealm()).toBe("");

    // even setting the default realm keeps an empty string as the realm is not in the options list
    realmService.setDefaultRealm("realm1");
    expect(userService.selectedUserRealm()).toBe("");
  });

  it("selectedUserRealm should expose first realm if no default realm is not in the realmOptions list", () => {
    realmService.realmOptions.set(["realm1", "realm2"]);
    realmService.setDefaultRealm("someRealm");
    expect(userService.selectedUserRealm()).toBe("realm1");
  });

  it("selectedUserRealm uses the opened user's realm on user details", () => {
    contentServiceMock.onUserDetails = signal(true);
    contentServiceMock.detailsUser.set({ username: "Alice", realm: "userRealm" });
    expect(userService.selectedUserRealm()).toBe("userRealm");
  });

  it("allUsernames exposes every user.username", () => {
    expect(userService.allUsernames()).toEqual(["Alice", "Bob", "Charlie"]);
  });

  it("displayUser returns the username for objects and echoes raw strings", () => {
    expect(userService.displayUser(alice)).toBe("Alice");
    expect(userService.displayUser("plainString")).toBe("plainString");
  });

  describe("pageSize", () => {
    it("pageSize should be initialized with policy value", () => {
      authServiceMock.userPageSize.set(20);
      expect(userService.pageSize()).toBe(20);
    });

    it("pageSize should be 10 if policy value is invalid", () => {
      authServiceMock.userPageSize.set(0);
      expect(userService.pageSize()).toBe(10);
    });
  });

  describe("user filtering", () => {
    it("selectedUser returns null when userNameFilter is empty", () => {
      expect(userService.selectedUser()).toBeNull();
    });

    it("selectedUser returns the matching user when userNameFilter is set", () => {
      userService.selectionFilter.set("Alice");
      expect(userService.selectedUser()).toEqual(alice);
    });

    it("filteredUsers narrows the list by the string in userFilter (case-insensitive)", () => {
      userService.selectionFilter.set("aL"); // any case
      expect(userService.selectionFilteredUsers()).toEqual([users[0]]);
    });

    it("should return all users when filter is empty", () => {
      userService.selectionFilter.set("");
      expect(userService.selectionFilteredUsers()).toEqual(users);
    });
  });

  describe("attribute policy + attributes", () => {
    it("setUserAttribute issues POST /user/attribute with params", () => {
      realmService.realmOptions.set(["realm1", "realm2"]);
      userService.setUserAttribute("department", "finance").subscribe();

      const req = httpMock.expectOne((r) => r.method === "POST" && r.url.endsWith("/user/attribute"));
      expect(req.request.params.get("user")).toBe("Alice");
      expect(req.request.params.get("realm")).toBe("realm1");
      expect(req.request.params.get("key")).toBe("department");
      expect(req.request.params.get("value")).toBe("finance");

      req.flush({ result: { value: 123 } });
    });

    it("deleteUserAttribute issues DELETE /user/attribute/<key>/<user>/<realm> with proper encoding", () => {
      realmService.realmOptions.set(["realm1", "r 1"]);
      userService.detailsUser.set({ username: "Alice Smith", realm: "" });
      realmService.setDefaultRealm("r 1");

      const key = "department/role";
      userService.deleteUserAttribute(key).subscribe();

      const expectedEnding =
        "/user/attribute/" +
        encodeURIComponent(key) +
        "/" +
        encodeURIComponent("Alice Smith") +
        "/" +
        encodeURIComponent("r 1");

      const req = httpMock.expectOne((r) => r.method === "DELETE" && r.url.endsWith(expectedEnding));

      expect(req.request.headers).toBeTruthy();

      req.flush({ result: { status: true, value: true } });
    });
  });

  describe("attribute policy + attributes (no HTTP; drive signals directly)", () => {
    it("attributePolicy defaults when attributesResource has no value", () => {
      expect(userService.attributePolicy()).toEqual({ delete: [], set: {} });
      expect(userService.deletableAttributes()).toEqual([]);
      expect(userService.attributeSetMap()).toEqual({});
      expect(userService.hasWildcardKey()).toBe(false);
      expect(userService.keyOptions()).toEqual([]);
    });

    it("derives deletableAttributes, wildcard, and sorted keyOptions from editableAttributesResource value", () => {
      const policy: UserAttributePolicy = {
        delete: ["department", "attr2", "attr1"],
        set: {
          "*": ["2", "1"],
          city: ["*"],
          department: ["sales", "finance"]
        }
      };

      (userService as {
        editableAttributesResource: UserService["editableAttributesResource"]
      }).editableAttributesResource =
        new MockHttpResourceRef(MockPiResponse.fromValue(policy)) as unknown as UserService["editableAttributesResource"];

      expect(userService.attributePolicy()).toEqual(policy);
      expect(userService.deletableAttributes()).toEqual(["department", "attr2", "attr1"]);
      expect(userService.attributeSetMap()).toEqual(policy.set);
      expect(userService.hasWildcardKey()).toBe(true);
      expect(userService.keyOptions()).toEqual(["city", "department"]);
    });

    it("userAttributes and userAttributesList derive from userAttributesResource value", () => {
      const attrs = { city: "Berlin", department: ["sales", "finance"] };

      (userService as { userAttributesResource: UserService["userAttributesResource"] }).userAttributesResource =
        new MockHttpResourceRef(MockPiResponse.fromValue(attrs)) as unknown as UserService["userAttributesResource"];

      expect(userService.userAttributes()).toEqual(attrs);
      expect(userService.userAttributesList()).toEqual([
        { key: "city", value: "Berlin" },
        { key: "department", value: "sales, finance" }
      ]);
    });

    it("userAttributes falls back to {} when userAttributesResource becomes undefined", () => {
      const ref = new MockHttpResourceRef(MockPiResponse.fromValue({ city: "Berlin" }));
      (userService as { userAttributesResource: UserService["userAttributesResource"] }).userAttributesResource =
        ref as unknown as UserService["userAttributesResource"];

      expect(userService.userAttributes()).toEqual({ city: "Berlin" });

      ref.set(undefined as unknown as MockPiResponse<{ city: string }>);

      expect(userService.userAttributes()).toEqual({});
      expect(userService.userAttributesList()).toEqual([]);
    });

    it("userAttributes handle http error of userAttributesResource", async () => {
      contentServiceMock.onUserDetails = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/user/attribute");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(userService.userAttributes()).toEqual({});
      expect(userService.userAttributesList()).toEqual([]);

      httpMock.expectOne((r) => r.url.includes("/user/editable_attributes"));
    });

    it("resetFilter replaces apiUserFilter with a fresh instance", () => {
      const before = userService.apiUserFilter();
      userService.resetFilter();
      const after = userService.apiUserFilter();

      expect(after).not.toBe(before);
      expect(userService.filterParams()).toEqual({});
    });
  });

  it("should not include empty filter values in filterParams", () => {
    userService.apiUserFilter.set({
      filterMap: new Map([
        ["username", ""],
        ["email", "alice@test"],
        ["givenname", "   "],
        ["surname", "*"]
      ])
    } as Partial<FilterValue> as FilterValue);

    const params = userService.filterParams();
    expect(params).not.toHaveProperty("username");
    expect(params).not.toHaveProperty("givenname");
    expect(params).toHaveProperty("email", "*alice@test*");
    expect(params).not.toHaveProperty("surname");
  });

  describe("editableAttributesResource / attributePolicy", () => {
    it("attributePolicy falls back to default when resource empty", () => {
      expect(userService.attributePolicy()).toEqual({ delete: [], set: {} });
    });

    it("should update attributePolicy from editableAttributesResource on successful response", async () => {
      contentServiceMock.onUserDetails = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/user/editable_attributes/");
      expect(req.request.method).toBe("GET");
      const attributePolicy = { delete: ["test1", "test2"], set: { test2: ["*"], test3: ["opt1", "opt2"] } };
      req.flush(MockPiResponse.fromValue(attributePolicy));
      await Promise.resolve();

      expect(userService.editableAttributesResource.hasValue()).toBe(true);
      expect(userService.attributePolicy()).toEqual(attributePolicy);

      httpMock.expectOne((r) => r.url.includes("/user/attribute"));
    });

    it("should handle error state from smsGatewayResource", async () => {
      contentServiceMock.onUserDetails = signal(true);
      TestBed.tick();

      const req = httpMock.expectOne((r) => r.url === "/user/editable_attributes/");
      expect(req.request.method).toBe("GET");
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });
      await Promise.resolve();

      expect(userService.editableAttributesResource.hasValue()).toBe(false);
      expect(userService.attributePolicy()).toEqual({ delete: [], set: {} });

      httpMock.expectOne((r) => r.url.includes("/user/attribute"));
    });
  });

  describe("selectedUser", () => {
    let contentService: MockContentService;
    let authService: MockAuthService;

    beforeEach(() => {
      contentService = TestBed.inject(ContentService) as unknown as MockContentService;
      authService = TestBed.inject(AuthService) as unknown as MockAuthService;

      contentService.routeUrl.set(ROUTE_PATHS.USERS);
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "admin", username: "enduser" });

      userService.selectionFilter.set("");
      userService.selectedUserRealm.set("realm1");
      userService.usersResource = new MockHttpResourceRef(MockPiResponse.fromValue(users));
    });

    it("returns null when no token username, role != user, and selection filter empty", () => {
      expect(userService.selectedUser()).toBeNull();
    });

    it("returns matching user when selection filter is a string", () => {
      userService.selectionFilter.set("Alice");
      expect(userService.selectedUser()).toEqual(alice);
    });

    it("returns matching user when selection filter is a UserData object", () => {
      userService.selectionFilter.set(users[1]);
      expect(userService.selectedUser()).toEqual(users[1]);
    });

    it("returns username when on token detail route and token has username", () => {
      contentService.routeUrl.set(ROUTE_PATHS.TOKENS_DETAILS);

      setTokenDetailUsername("Bob");

      userService.selectionFilter.set("Alice");
      expect(userService.selectedUser()).toEqual(users[1]);
    });

    it("when role is 'user': returns the authenticated username", () => {
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "user", username: "Charlie" });

      userService.selectionFilter.set("");
      expect(userService.selectedUser()).toEqual(users[2]);
    });
  });

  describe("userResource", () => {
    beforeEach(() => {
      jest.spyOn(authServiceMock, "actionAllowed").mockImplementation((action: string) => action === "userlist");
    });

    it("should return undefined if route is not USER_DETAILS", async () => {
      contentServiceMock.routeUrl.update(() => ROUTE_PATHS.TOKENS);
      const mockBackend = TestBed.inject(HttpTestingController);
      TestBed.tick();

      // Expect and flush the HTTP request
      mockBackend.expectNone(environment.proxyUrl + "/user/");
      await Promise.resolve();

      expect(userService.userResource.value()).toBeUndefined();
    });

    it("should do request if route is USER_DETAILS", async () => {
      const realm = "test-realm";
      const user = "alice";
      contentServiceMock.routeUrl.update(() => ROUTE_PATHS.USERS_DETAILS + "/" + user);
      userService.detailsUser.set({ username: user, realm: "" });
      userService.selectedUserRealm.set(realm);
      const mockBackend = TestBed.inject(HttpTestingController);
      TestBed.tick();

      // Expect and flush the main user details request
      const req = mockBackend.expectOne(environment.proxyUrl + "/user/?user=" + user + "&realm=" + realm);
      req.flush({ result: {} });

      // Ignore and flush all other open requests
      httpMock.match(() => true).forEach((r) => r.flush({ result: {} }));

      await Promise.resolve();

      expect(userService.userResource.value()).toBeDefined();
      expect(userService.usersResource.value()).toBeUndefined();
    });

    it("should handle http errors", async () => {
      const realm = "test-realm";
      const user = "alice";
      contentServiceMock.routeUrl.update(() => ROUTE_PATHS.USERS_DETAILS + "/" + user);
      userService.detailsUser.set({ username: user, realm: "" });
      userService.selectedUserRealm.set(realm);
      const mockBackend = TestBed.inject(HttpTestingController);
      TestBed.tick();

      // Expect and flush an error response
      const req = mockBackend.expectOne(environment.proxyUrl + "/user/?user=" + user + "&realm=" + realm);
      req.flush(MockPiResponse.fromError({ message: "Permission denied" }), {
        status: 403,
        statusText: "Permission denied"
      });

      // Ignore and flush all other open requests
      httpMock.match(() => true).forEach((r) => r.flush({ result: {} }));

      await Promise.resolve();

      expect(userService.userResource.hasValue()).toBe(false);
      expect(userService.usersResource.hasValue()).toBe(false);
      expect(userService.user()).toEqual({
        description: "",
        editable: false,
        email: "",
        givenname: "",
        mobile: "",
        phone: "",
        resolver: "",
        surname: "",
        userid: "",
        username: ""
      });
      expect(userService.users()).toEqual([]);
    });

    it("should not show previous user details when detailsUsername changes", async () => {
      const realm = "test-realm";
      contentServiceMock.routeUrl.update(() => ROUTE_PATHS.USERS_DETAILS + "/alice");
      userService.detailsUser.set({ username: "alice", realm: "" });
      userService.selectedUserRealm.set(realm);
      const mockBackend = TestBed.inject(HttpTestingController);
      TestBed.tick();

      // Load alice
      const req1 = mockBackend.expectOne(environment.proxyUrl + "/user/?user=alice&realm=" + realm);
      req1.flush(MockPiResponse.fromValue([buildUser("alice")]));
      httpMock.match(() => true).forEach((r) => r.flush({ result: {} }));
      await Promise.resolve();

      expect(userService.user().username).toBe("alice");

      // Switch to bob — while loading, user signal should NOT keep alice's data
      contentServiceMock.routeUrl.update(() => ROUTE_PATHS.USERS_DETAILS + "/bob");
      userService.detailsUser.set({ username: "bob", realm: "" });
      TestBed.tick();

      // Before bob's response arrives, user should be reset to empty
      expect(userService.user().username).toBe("");

      const req2 = mockBackend.expectOne(environment.proxyUrl + "/user/?user=bob&realm=" + realm);
      req2.flush(MockPiResponse.fromValue([buildUser("bob")]));
      httpMock.match(() => true).forEach((r) => r.flush({ result: {} }));
      await Promise.resolve();

      expect(userService.user().username).toBe("bob");
    });
  });

  describe("users signal (list)", () => {
    beforeEach(() => {
      jest.spyOn(authServiceMock, "actionAllowed").mockImplementation((action: string) => action === "userlist");
    });

    it("should clear users when changing realm even if request fails", async () => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.USERS);
      userService.selectedUserRealm.set("other");
      TestBed.tick();
      httpMock.match(() => true).forEach((r) => r.flush({ result: { value: [] } }));

      userService.selectedUserRealm.set("realm1");
      userService.users();
      TestBed.tick();

      const req1 = httpMock.expectOne((req) => req.url.includes("/user") && req.params.get("realm") === "realm1");
      req1.flush(MockPiResponse.fromValue([buildUser("user1")]));
      await Promise.resolve();
      TestBed.tick();

      expect(userService.users()).toHaveLength(1);
      expect(userService.users()[0].username).toBe("user1");

      userService.selectedUserRealm.set("realm2");
      userService.users();
      TestBed.tick();

      expect(userService.users()).toHaveLength(0);

      const req2 = httpMock.expectOne((req) => req.url.includes("/user") && req.params.get("realm") === "realm2");
      req2.flush("Error", { status: 500, statusText: "Server Error" });
      await Promise.resolve();
      TestBed.tick();

      expect(userService.users()).toHaveLength(0);
    });
  });

  describe("UserService createUser", () => {
    it("should create user successfully", () => {
      const resolver = "test";
      const userData: EditUserData = { username: "new-user" };
      let resultValue: boolean | undefined;
      userService.createUser(resolver, userData).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "POST" && r.url.includes("/user/"));
      req.flush({ result: { value: true, status: true } });
      expect(resultValue).toBe(true);
      expect(req.request.body).toEqual({ user: "new-user", resolver });
    });

    it("should handle shallow failure of creating user", () => {
      const resolver = "test";
      const userData: EditUserData = { username: "new-user" };
      let resultValue: boolean | undefined;
      userService.createUser(resolver, userData).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "POST" && r.url.includes("/user/"));
      req.flush({ result: { value: true, status: false } });
      expect(resultValue).toBe(false);
      expect(req.request.body).toEqual({ user: "new-user", resolver });
    });

    it("should handle create user failure", () => {
      const resolver = "test";
      const userData: EditUserData = { username: "fail-user" };
      let resultValue: boolean | undefined;
      userService.createUser(resolver, userData).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "POST" && r.url.includes("/user/"));
      req.flush(
        { result: { status: false, error: { message: "fail message" } } },
        { status: 500, statusText: "Server Error" }
      );
      expect(resultValue).toBe(false);
      expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to create user fail-user. fail" + " message");
    });
  });

  describe("UserService editUser", () => {
    it("should edit user successfully", () => {
      const resolver = "test";
      const userData: EditUserData = { username: "edit-user" };
      let resultValue: boolean | undefined;
      userService.editUser(resolver, userData).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "PUT" && r.url.includes("/user/"));
      req.flush({ result: { value: true, status: true } });
      expect(resultValue).toBe(true);
      expect(req.request.body).toEqual({ user: "edit-user", resolver });
    });

    it("should handle shallow edit user failure", () => {
      const resolver = "test";
      const userData: EditUserData = { username: "edit-user" };
      let resultValue: boolean | undefined;
      userService.editUser(resolver, userData).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "PUT" && r.url.includes("/user/"));
      req.flush({ result: { value: true, status: false } });
      expect(resultValue).toBe(false);
      expect(req.request.body).toEqual({ user: "edit-user", resolver });
    });

    it("should handle edit user failure", () => {
      const resolver = "test";
      const userData: EditUserData = { username: "fail-user" };
      let resultValue: boolean | undefined;
      userService.editUser(resolver, userData).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "PUT" && r.url.includes("/user/"));
      req.flush({ result: { status: false, error: { message: "fail" } } }, { status: 500, statusText: "Server Error" });
      expect(resultValue).toBe(false);
      expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to update user fail-user. fail");
    });
  });

  describe("UserService deleteUser", () => {
    it("should delete user successfully", () => {
      const resolver = "test";
      const username = "deleteuser";
      let resultValue: boolean | undefined;
      userService.deleteUser(resolver, username).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "DELETE" && r.url.includes("/user/"));
      req.flush({ result: { value: true, status: true } });
      expect(resultValue).toBe(true);
    });

    it("should handle shallow failure", () => {
      const resolver = "test";
      const username = "deleteuser";
      let resultValue: boolean | undefined;
      userService.deleteUser(resolver, username).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "DELETE" && r.url.includes("/user/"));
      req.flush({ result: { value: true, status: false } });
      expect(resultValue).toBe(false);
    });

    it("should handle delete user failure", () => {
      const resolver = "test";
      const username = "fail-user";
      let resultValue: boolean | undefined;
      userService.deleteUser(resolver, username).subscribe((result) => {
        resultValue = result;
      });
      const req = httpMock.expectOne((r) => r.method === "DELETE" && r.url.includes("/user/"));
      req.flush({ result: { error: { message: "fail" } } }, { status: 500, statusText: "Server Error" });
      expect(resultValue).toBe(false);
      expect(notificationServiceMock.error).toHaveBeenCalledWith("Failed to delete user fail-user. fail");
    });
  });
});
