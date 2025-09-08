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
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { HttpResourceRef, httpResource } from "@angular/common/http";
import { Injectable, Signal, WritableSignal, computed, inject, linkedSignal, signal } from "@angular/core";
import { RealmService, RealmServiceInterface } from "../realm/realm.service";
import { TokenService, TokenServiceInterface } from "../token/token.service";

import { FilterValue } from "../../core/models/filter_value";
import { PiResponse } from "../../app.component";
import { Sort } from "@angular/material/sort";
import { environment } from "../../../environments/environment";
import { ROUTE_PATHS } from "../../route_paths";

const apiFilter = ["description", "email", "givenname", "mobile", "phone", "resolver", "surname", "userid", "username"];
const advancedApiFilter: string[] = [];

export interface UserData {
  description: string;
  editable: boolean;
  email: string;
  givenname: string;
  mobile: string;
  phone: string;
  resolver: string;
  surname: string;
  userid: string;
  username: string;
}

export interface UserServiceInterface {
  selectedUser: Signal<UserData | null>;
  selectionFilter: WritableSignal<string | UserData | null>;
  selectionFilteredUsers: Signal<UserData[]>;

  allUsernames: Signal<string[]>;
  selectionUsernameFilter: Signal<string>;
  selectionFilteredUsernames: Signal<string[]>;

  selectedUserRealm: WritableSignal<string>;

  userResource: HttpResourceRef<PiResponse<UserData[]> | undefined>;
  user: WritableSignal<UserData>;
  usersResource: HttpResourceRef<PiResponse<UserData[]> | undefined>;
  users: WritableSignal<UserData[]>;

  apiUserFilter: WritableSignal<FilterValue>;
  pageIndex: WritableSignal<number>;
  pageSize: WritableSignal<number>;
  apiFilterOptions: string[];
  advancedApiFilterOptions: string[];
  resetFilter(): void;
  handleFilterInput($event: Event): void;

  displayUser(user: UserData | string): string;
}

@Injectable({
  providedIn: "root"
})
export class UserService implements UserServiceInterface {
  private readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  readonly apiFilterOptions = apiFilter;
  readonly advancedApiFilterOptions = advancedApiFilter;
  private baseUrl = environment.proxyUrl + "/user/";
  apiUserFilter = signal(new FilterValue());
  filterParams = computed<Record<string, string>>(() => {
    const allowedFilters = [...this.apiFilterOptions, ...this.advancedApiFilterOptions];
    const filterPairs = Array.from(this.apiUserFilter().filterMap.entries())
      .map(([key, value]) => ({ key, value }))
      .filter(({ key }) => allowedFilters.includes(key));
    if (filterPairs.length === 0) {
      return {};
    }
    return filterPairs.reduce(
      (acc, { key, value }) => ({
        ...acc,
        [key]: `*${value}*`
      }),
      {} as Record<string, string>
    );
  });

  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;

  filterValue = signal({} as Record<string, string>);

  pageSize = linkedSignal({
    source: () => this.authService.userPageSize(),
    computation: (pageSize) => (pageSize > 0 ? pageSize : 10)
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.apiUserFilter(),
      pageSize: this.pageSize(),
      routeUrl: this.contentService.routeUrl()
    }),
    computation: () => 0
  });
  selectedUserRealm = linkedSignal({
    source: () => ({
      routeUrl: this.contentService.routeUrl(),
      defaultRealm: this.realmService.defaultRealm(),
      selectedTokenType: this.tokenService.selectedTokenType(),
      authRole: this.authService.role(),
      authRealm: this.authService.realm()
    }),
    computation: (source) => {
      if (source.authRole === "user") {
        return source.authRealm;
      }
      return source.defaultRealm;
    }
  });
  selectionFilter = linkedSignal<string, UserData | string>({
    source: this.selectedUserRealm,
    computation: () => ""
  });
  selectionUsernameFilter = computed<string>(() => {
    const filter = this.selectionFilter();
    if (typeof filter === "string") {
      return filter;
    }
    return filter?.username ?? "";
  });
  userResource = httpResource<PiResponse<UserData[]>>(() => {
    if (!this.authService.actionAllowed("userlist")) {
      return undefined;
    }
    return {
      url: this.baseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });
  user: WritableSignal<UserData> = linkedSignal({
    source: this.userResource.value,
    computation: (source, previous) => {
      return (
        source?.result?.value?.[0] ??
        previous?.value ?? {
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
        }
      );
    }
  });
  usersResource = httpResource<PiResponse<UserData[]>>(() => {
    const selectedUserRealm = this.selectedUserRealm();
    if (
      selectedUserRealm === "" ||
      !this.authService.actionAllowed("userlist") ||
      (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS) &&
        !this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS) &&
        ![
          ROUTE_PATHS.TOKENS,
          ROUTE_PATHS.USERS,
          ROUTE_PATHS.TOKENS_CONTAINERS_CREATE,
          ROUTE_PATHS.TOKENS_ENROLLMENT
        ].includes(this.contentService.routeUrl()))
    ) {
      return undefined;
    }
    return {
      url: this.baseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        realm: selectedUserRealm,
        ...this.filterParams()
      }
    };
  });

  users: WritableSignal<UserData[]> = linkedSignal({
    source: this.usersResource.value,
    computation: (source, previous) => source?.result?.value ?? previous?.value ?? []
  });
  selectedUser = computed<UserData | null>(() => {
    var userName = "";
    if (this.authService.role() === "user") {
      userName = this.authService.username();
    } else {
      userName = this.selectionUsernameFilter();
    }
    if (!userName) {
      return null;
    }
    const users = this.users();
    const user = users.find((user) => user.username === userName);
    if (user) {
      return user;
    } else {
      return null;
    }
  });
  allUsernames = computed<string[]>(() => this.users().map((user) => user.username));
  selectionFilteredUsers = computed<UserData[]>(() => {
    var userFilter = this.selectionFilter();
    if (typeof userFilter !== "string" || userFilter.trim() === "") {
      return this.users();
    }
    const filterValue = userFilter.toLowerCase().trim();
    return this.users().filter((user) => user.username.toLowerCase().includes(filterValue));
  });
  selectionFilteredUsernames = computed<string[]>(() => this.selectionFilteredUsers().map((user) => user.username));

  displayUser(user: UserData | string): string {
    if (typeof user === "string") {
      return user;
    }
    return user ? user.username : "";
  }

  resetFilter(): void {
    this.apiUserFilter.set(new FilterValue());
  }
  handleFilterInput($event: Event): void {
    const input = $event.target as HTMLInputElement;
    const newFilter = this.apiUserFilter().copyWith({ value: input.value });
    this.apiUserFilter.set(newFilter);
  }
}
