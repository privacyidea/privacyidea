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
import { linkedSignal, Signal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { UserAttributePolicy, UserData, UserServiceInterface } from "@services/user/user.service";
import { of } from "rxjs";
import { Debouncer } from "@utils/debounce.utils";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockUserService implements UserServiceInterface {
  userAttributes: Signal<Record<string, string>> = signal({});
  userAttributesList = signal<{ key: string; value: string }[]>([]);
  userAttributesResource: HttpResourceRef<PiResponse<Record<string, string>, unknown> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue({}));
  internalAttributes: Signal<Record<string, string>> = signal({});
  internalAttributesList = signal<{ key: string; value: string }[]>([]);
  internalAttributesResource: HttpResourceRef<PiResponse<Record<string, string>, unknown> | undefined> =
    new MockHttpResourceRef(MockPiResponse.fromValue({}));
  attributePolicy: Signal<UserAttributePolicy> = signal<UserAttributePolicy>({
    delete: ["department", "attr2", "attr1"],
    set: { "*": ["2", "1"], city: ["*"], department: ["sales", "finance"] }
  });
  deletableAttributes: Signal<string[]> = signal([]);
  attributeSetMap = signal<Record<string, string[]>>({});
  hasWildcardKey: Signal<boolean> = signal(false);
  keyOptions: Signal<string[]> = signal([]);
  selectedUser = signal<UserData | null>(null);
  usersOfRealmResource: HttpResourceRef<PiResponse<UserData[], undefined> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  selectedUsername = signal("");
  setDefaultRealm = jest.fn();

  resetUserSelection() {
    this.selectionFilter.set("");
    this.selectedUserRealm.set("");
  }

  detailsUser = signal({ username: "", realm: "" });

  setUserAttribute = jest.fn().mockReturnValue(of({}));
  deleteUserAttribute = jest.fn().mockReturnValue(of({}));

  clearFilter = jest.fn().mockImplementation(() => {
    this.activeFilter.set(new FilterValue());
  });

  filterFromInput = jest.fn().mockImplementation(($event: Event) => {
    const inputElement = $event.target as HTMLInputElement;
    return new FilterValue({ value: inputElement.value });
  });

  handleFilterInput = jest.fn().mockImplementation(($event: Event) => {
    this.activeFilter.set(this.filterFromInput($event));
  });

  applyFilterInput = jest.fn().mockImplementation(($event: Event) => {
    this.activeFilter.set(this.filterFromInput($event));
  });

  activeFilter = signal(new FilterValue());
  filterDebouncer = new Debouncer(this.activeFilter);
  filterDraft = this.activeFilter;
  filterParams = signal<Record<string, string>>({});
  setFilter = jest.fn().mockImplementation((filter: FilterValue) => {
    this.activeFilter.set(filter);
  });
  updateFilter = jest.fn().mockImplementation((computeFilter: (current: FilterValue) => FilterValue) => {
    this.activeFilter.set(computeFilter(this.activeFilter()));
  });
  pageIndex = signal(0);
  sort = signal<Sort>({ active: "", direction: "" });
  pageSize = signal(10);
  apiFilterKeys: string[] = [];
  advancedApiFilterKeys: string[] = [];
  hiddenApiFilterKeys: string[] = [];
  apiFilterKeyMap: Record<string, string> = {};
  exactMatchKeys = new Set<string>();
  allFilterKeys: Signal<string[]> = signal([
    ...this.apiFilterKeys,
    ...this.advancedApiFilterKeys,
    ...this.hiddenApiFilterKeys
  ]);

  userResource: HttpResourceRef<PiResponse<UserData[]> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );

  user = signal<UserData>({
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

  users = signal<UserData[]>([]);
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

  createUser = jest.fn();
  editUser = jest.fn();
  deleteUser = jest.fn();
}
