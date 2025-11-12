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
import { TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { UserData, UserService } from "./user.service";
import { RealmService } from "../realm/realm.service";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";
import { Tokens, TokenService } from "../token/token.service";

import {
  MockAuthService,
  MockContentService, MockHttpResourceRef,
  MockLocalService,
  MockNotificationService, MockPiResponse,
  MockRealmService,
  MockTokenService
} from "../../../testing/mock-services";
import { ROUTE_PATHS } from "../../route_paths";
import { PiResponse } from "../../app.component";

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
    const seeded = MockPiResponse.fromValue<Tokens>(
      { tokens: [{ username: name } as any] } as any
    ) as unknown as PiResponse<Tokens>;
    ref.set(seeded);
    return;
  }

  ref.update((resp) => {
    const current = resp!.result!.value as unknown as Tokens;
    const first = (current.tokens?.[0] ?? {}) as any;
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
        MockLocalService,
        MockNotificationService
      ]
    });

    userService = TestBed.inject(UserService);
    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;
    httpMock = TestBed.inject(HttpTestingController);

    alice = buildUser("Alice");
    users = [alice, buildUser("Bob"), buildUser("Charlie")];
    userService.users.set(users);
    userService.detailsUsername.set("Alice");
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(userService).toBeTruthy();
  });

  it("selectedUserRealm should expose the current defaultRealm", () => {
    expect(userService.selectedUserRealm()).toBe("realm1");
    realmService.defaultRealm.set("someRealm");
    expect(userService.selectedUserRealm()).toBe("someRealm");
  });

  it("allUsernames exposes every user.username", () => {
    expect(userService.allUsernames()).toEqual(["Alice", "Bob", "Charlie"]);
  });

  it("displayUser returns the username for objects and echoes raw strings", () => {
    expect(userService.displayUser(alice)).toBe("Alice");
    expect(userService.displayUser("plainString")).toBe("plainString");
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
      userService.setUserAttribute("department", "finance").subscribe();

      const req = httpMock.expectOne(r =>
        r.method === "POST" && r.url.endsWith("/user/attribute")
      );
      expect(req.request.params.get("user")).toBe("Alice");
      expect(req.request.params.get("realm")).toBe("realm1");
      expect(req.request.params.get("key")).toBe("department");
      expect(req.request.params.get("value")).toBe("finance");

      req.flush({ result: { value: 123 } });
    });

    it("deleteUserAttribute issues DELETE /user/attribute/<key>/<user>/<realm> with proper encoding", () => {
      userService.detailsUsername.set("Alice Smith");
      realmService.defaultRealm.set("r 1");

      const key = "department/role";
      userService.deleteUserAttribute(key).subscribe();

      const expectedEnding =
        "/user/attribute/" +
        encodeURIComponent(key) +
        "/" +
        encodeURIComponent("Alice Smith") +
        "/" +
        encodeURIComponent("r 1");

      const req = httpMock.expectOne(r =>
        r.method === "DELETE" && r.url.endsWith(expectedEnding)
      );

      expect(req.request.headers).toBeTruthy();

      req.flush({ result: { status: true, value: true } });
    });
  });

  describe("attribute policy + attributes (no HTTP; drive signals directly)", () => {
    it("attributePolicy defaults when attributesResource has no value", () => {
      (userService as any).attributesResource = new MockHttpResourceRef<
        any | undefined
      >(undefined as any);

      expect(userService.attributePolicy()).toEqual({ delete: [], set: {} });
      expect(userService.deletableAttributes()).toEqual([]);
      expect(userService.attributeSetMap()).toEqual({});
      expect(userService.hasWildcardKey()).toBe(false);
      expect(userService.keyOptions()).toEqual([]);
    });

    it("derives deletableAttributes, wildcard, and sorted keyOptions from attributesResource value", () => {
      const policy = {
        delete: ["department", "attr2", "attr1"],
        set: {
          "*": ["2", "1"],
          city: ["*"],
          department: ["sales", "finance"]
        }
      };

      (userService as any).attributesResource = new MockHttpResourceRef(
        MockPiResponse.fromValue(policy)
      );

      expect(userService.attributePolicy()).toEqual(policy);
      expect(userService.deletableAttributes()).toEqual(["department", "attr2", "attr1"]);
      expect(userService.attributeSetMap()).toEqual(policy.set);
      expect(userService.hasWildcardKey()).toBe(true);
      expect(userService.keyOptions()).toEqual(["city", "department"]);
    });

    it("userAttributes and userAttributesList derive from userAttributesResource value", () => {
      const attrs = { city: "Berlin", department: ["sales", "finance"] };

      (userService as any).userAttributesResource = new MockHttpResourceRef(
        MockPiResponse.fromValue(attrs)
      );

      expect(userService.userAttributes()).toEqual(attrs);
      expect(userService.userAttributesList()).toEqual([
        { key: "city", value: "Berlin" },
        { key: "department", value: "sales, finance" }
      ]);
    });

    it("userAttributes falls back to {} when userAttributesResource becomes undefined", () => {
      const ref = new MockHttpResourceRef(
        MockPiResponse.fromValue({ city: "Berlin" })
      );
      (userService as any).userAttributesResource = ref;

      expect(userService.userAttributes()).toEqual({ city: "Berlin" });

      ref.set(undefined as any);

      expect(userService.userAttributes()).toEqual({});
      expect(userService.userAttributesList()).toEqual([]);
    });

    it("resetFilter replaces apiUserFilter with a fresh instance", () => {
      const before = userService.apiUserFilter();
      userService.resetFilter();
      const after = userService.apiUserFilter();

      expect(after).not.toBe(before);
      expect(userService.filterParams()).toEqual({});
    });
  });

  describe("selectedUser", () => {
    let contentService: MockContentService;
    let tokenService: MockTokenService;
    let authService: MockAuthService;

    beforeEach(() => {
      contentService = TestBed.inject(ContentService) as unknown as MockContentService;
      tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
      authService = TestBed.inject(AuthService) as unknown as MockAuthService;

      contentService.routeUrl.set(ROUTE_PATHS.USERS);
      authService.role.set("admin");
      authService.username.set("enduser");
      tokenService.tokenDetailResource = new MockHttpResourceRef(undefined as any);
      userService.selectionFilter.set("");
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

    it('when role is "user": returns the authenticated username', () => {
      authService.role.set("user");
      authService.username.set("Charlie");

      userService.selectionFilter.set("");
      expect(userService.selectedUser()).toEqual(users[2]);
    });
  });
});
