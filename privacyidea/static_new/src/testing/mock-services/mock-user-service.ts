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
import { HttpResourceRef } from "@angular/common/http";
import { computed, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { Observable, of } from "rxjs";
import { PiResponse } from "../../app/app.component";
import { FilterValue } from "../../app/core/models/filter_value";
import { UserAttributePolicy, UserData, UserServiceInterface } from "../../app/services/user/user.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockUserService implements UserServiceInterface {
  userAttributes: Signal<Record<string, string>> = signal({});
  userAttributesList: WritableSignal<{ key: string; value: string }[]> = signal([]);
  userAttributesResource: HttpResourceRef<PiResponse<Record<string, string>, unknown> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue({}));
  attributePolicy: Signal<UserAttributePolicy> = signal<UserAttributePolicy>({
    delete: ["department", "attr2", "attr1"],
    set: { "*": ["2", "1"], city: ["*"], department: ["sales", "finance"] }
  });
  deletableAttributes: Signal<string[]> = signal([]);
  attributeSetMap = signal<Record<string, string[]>>({});
  hasWildcardKey: Signal<boolean> = signal(false);
  keyOptions: Signal<string[]> = signal([]);
  selectedUser: WritableSignal<UserData | null> = signal(null);
  usersOfRealmResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  selectedUsername = signal("");
  setDefaultRealm = jest.fn();

  resetUserSelection() {
    this.selectionFilter.set("");
    this.selectedUserRealm.set("");
  }

  detailsUsername: WritableSignal<string> = signal("");

  setUserAttribute = jest.fn().mockReturnValue(of({}));
  deleteUserAttribute = jest.fn().mockReturnValue(of({}));

  resetFilter = jest.fn().mockImplementation(() => {
    this.apiUserFilter.set(new FilterValue());
  });

  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    const inputElement = $event.target as HTMLInputElement;
    this.apiUserFilter.set(new FilterValue({ value: inputElement.value }));
  });

  apiUserFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  pageIndex: WritableSignal<number> = signal(0);
  pageSize: WritableSignal<number> = signal(10);
  apiFilterOptions: string[] = [];
  advancedApiFilterOptions: string[] = [];

  userResource: HttpResourceRef<PiResponse<UserData[]> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );

  user: WritableSignal<UserData> = signal({
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

  usersResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );

  users: WritableSignal<UserData[]> = signal([]);
  allUsernames: Signal<string[]> = signal([]);

  selectionFilteredUsernames: Signal<string[]> = signal([]);
  selectedUserRealm = signal("");

  selectionFilter = linkedSignal<string, UserData | string>({ source: this.selectedUserRealm, computation: () => "" });

  selectionUsernameFilter = linkedSignal<string>(() => {
    const filter = this.selectionFilter();
    if (typeof filter === "string") {
      return filter;
    }
    return filter?.username ?? "";
  });

  selectionFilteredUsers = signal<UserData[]>([]);

  displayUser = jest.fn().mockImplementation((user: UserData | string): string => {
    const name = typeof user === "string" ? user : (user?.username ?? "");
    this.selectedUsername.set(name);
    return name;
  });
}
