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
import { signal } from "@angular/core";
import { UserData, UserService } from "./user.service";
import { LocalService } from "../local/local.service";
import { RealmService } from "../realm/realm.service";
import { provideHttpClient } from "@angular/common/http";

class MockLocalService {
  getHeaders = jest.fn().mockReturnValue({ Authorization: "Bearer FAKE_TOKEN" });
}

class MockRealmService {
  defaultRealm = signal("defaultRealm");
}

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

describe("UserService", () => {
  let userService: UserService;
  let realmService: MockRealmService;
  let users: UserData[];
  let alice: UserData;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        UserService,
        { provide: LocalService, useClass: MockLocalService },
        { provide: RealmService, useClass: MockRealmService }
      ]
    });

    userService = TestBed.inject(UserService);
    realmService = TestBed.inject(RealmService) as unknown as MockRealmService;

    alice = buildUser("Alice");
    users = [alice, buildUser("Bob"), buildUser("Charlie")];
    userService.users.set(users);
  });

  it("should be created", () => {
    expect(userService).toBeTruthy();
  });

  it("selectedUserRealm should expose the current defaultRealm", () => {
    expect(userService.selectedUserRealm()).toBe("defaultRealm");
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
});
