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
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable, linkedSignal, Signal, signal, WritableSignal } from "@angular/core";
import { RealmService, RealmServiceInterface } from "../realm/realm.service";
import { TokenService, TokenServiceInterface } from "../token/token.service";

import { FilterValue } from "../../core/models/filter_value";
import { PiResponse } from "../../app.component";
import { environment } from "../../../environments/environment";
import { ROUTE_PATHS } from "../../route_paths";
import { StringUtils } from "../../utils/string.utils";
import { Observable } from "rxjs";

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
  [key: string]: unknown; // Allow additional custom properties
}

export interface UserAttributePolicy {
  delete: string[];
  set: Record<string, string[]>;
}

export interface UserServiceInterface {
  userAttributes: Signal<Record<string, string>>;
  userAttributesList: Signal<{ key: string; value: string }[]>;
  userAttributesResource: HttpResourceRef<PiResponse<Record<string, string>> | undefined>;

  attributePolicy: Signal<UserAttributePolicy>;
  deletableAttributes: Signal<string[]>;
  attributeSetMap: Signal<Record<string, string[]>>;
  hasWildcardKey: Signal<boolean>;
  keyOptions: Signal<string[]>;

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

  detailsUsername: WritableSignal<string>;

  setUserAttribute(key: string, value: string): Observable<PiResponse<number, unknown>>;

  deleteUserAttribute(key: string): Observable<PiResponse<any, unknown>>;

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
  private readonly http = inject(HttpClient);
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  private baseUrl = environment.proxyUrl + "/user/";
  filterValue = signal({} as Record<string, string>);
  readonly advancedApiFilterOptions = advancedApiFilter;

  filterParams = computed<Record<string, string>>(() => {
    const allowedFilters = [...this.apiFilterOptions, ...this.advancedApiFilterOptions];
    const entries = Array.from(this.apiUserFilter().filterMap.entries())
      .filter(([key]) => allowedFilters.includes(key))
      .map(([key, value]) => {
        const v = (value ?? "").toString().trim();
        return [key, v ? `*${v}*` : v] as const;
      })
      .filter(([, v]) => StringUtils.validFilterValue(v));
    return Object.fromEntries(entries) as Record<string, string>;
  });
  readonly apiFilterOptions = apiFilter;

  attributePolicy = computed<UserAttributePolicy>(
    () => this.editableAttributesResource.value()?.result?.value ?? { delete: [], set: {} }
  );

  deletableAttributes = computed<string[]>(() => this.attributePolicy().delete ?? []);

  editableAttributesResource = httpResource<PiResponse<UserAttributePolicy>>(() => {
    // Only load editable user attributes on the user details page.
    if (!this.contentService.onUserDetails()) {
      return undefined;
    }

    return {
      url: this.baseUrl + "editable_attributes/",
      method: "GET",
      headers: this.authService.getHeaders(),
      params: { user: this.detailsUsername(), realm: this.selectedUserRealm() }
    };
  });

  attributeSetMap = computed<Record<string, string[]>>(() => this.attributePolicy().set ?? {});

  hasWildcardKey = computed<boolean>(() => Object.prototype.hasOwnProperty.call(this.attributeSetMap(), "*"));

  keyOptions = computed<string[]>(() =>
    Object.keys(this.attributeSetMap())
      .filter((k) => k !== "*")
      .sort()
  );

  userAttributes = computed<Record<string, string>>(() => this.userAttributesResource.value()?.result?.value ?? {});

  userAttributesList = computed(() =>
    Object.entries(this.userAttributes()).map(([key, raw]) => ({
      key,
      value: Array.isArray(raw) ? raw.join(", ") : String(raw ?? "")
    }))
  );

  userAttributesResource = httpResource<PiResponse<Record<string, string>>>(() => {
    // Only load user attributes on the user details page.
    if (!this.contentService.onUserDetails()) {
      return undefined;
    }

    return {
      url: this.baseUrl + "attribute",
      method: "GET",
      headers: this.authService.getHeaders(),
      params: { user: this.detailsUsername(), realm: this.selectedUserRealm() }
    };
  });

  detailsUsername = this.tokenService.detailsUsername;

  apiUserFilter = signal(new FilterValue());

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

  selectedUserRealm: WritableSignal<string> = linkedSignal({
    source: () => ({
      routeUrl: this.contentService.routeUrl(),
      defaultRealm: this.realmService.defaultRealm(),
      selectedTokenType: this.tokenService.selectedTokenType(),
      authRole: this.authService.role(),
      authRealm: this.authService.realm()
    }),
    computation: (source, previous): string => {
      if (source.routeUrl.startsWith(ROUTE_PATHS.USERS) && previous?.value) {
        return previous.value;
      }
      return source.authRole === "user" ? source.authRealm : source.defaultRealm;
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
    // Do not load user details if the action is not allowed.
    if (!this.authService.actionAllowed("userlist")) {
      return undefined;
    }
    // Only load user details on the user details page.
    if (!this.contentService.onUserDetails()) {
      return undefined;
    }

    return {
      url: this.baseUrl,
      method: "GET",
      headers: this.authService.getHeaders(),
      params: {
        ...(this.detailsUsername() && { user: this.detailsUsername() }),
        ...(this.selectedUserRealm() && { realm: this.selectedUserRealm() })
      }
    };
  });

  user: WritableSignal<UserData> = linkedSignal({
    source: () => ({
      userResource: this.userResource.value,
      detailsUsername: this.detailsUsername()
    }),
    computation: (source, previous) => {
      return (
        source?.userResource()?.result?.value?.[0] ?? {
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
    const tokenSelection = this.tokenService.tokenSelection();
    // Do not load users if the action is not allowed.
    if (!this.authService.actionAllowed("userlist")) {
      return undefined;
    }
    // Load users only if a realm is selected.
    if (!selectedUserRealm) {
      return undefined;
    }
    // Only load users on routes with a user list or selection.
    const onAllowedRoute =
      this.contentService.onTokenDetails() ||
      this.contentService.onTokensContainersDetails() ||
      this.contentService.onTokens() ||
      this.contentService.onUsers() ||
      this.contentService.onTokensContainersCreate() ||
      this.contentService.onTokensEnrollment();

    if (!onAllowedRoute) {
      return undefined;
    }
    // On the tokens route we require at least one selected token before loading users.
    if (this.contentService.onTokens() && tokenSelection.length === 0) {
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
    let tokenUsername = "";
    if (this.contentService.onTokenDetails()) {
      const token = this.tokenService.tokenDetailResource.value()?.result?.value?.tokens?.[0];
      tokenUsername = token?.username ?? "";
    }

    let targetUsername = "";
    if (tokenUsername) {
      targetUsername = tokenUsername;
    } else if (this.authService.role() === "user") {
      targetUsername = this.authService.username();
    } else {
      targetUsername = this.selectionUsernameFilter();
      if (!targetUsername) {
        return null;
      }
    }

    const users = this.users();
    const found = users.find((u) => u.username === targetUsername);
    if (found) return found;

    return {
      username: targetUsername,
      description: "",
      editable: false,
      email: "",
      givenname: "",
      mobile: "",
      phone: "",
      resolver: "",
      surname: "",
      userid: ""
    } as UserData;
  });

  allUsernames = computed<string[]>(() => this.users().map((user) => user.username));

  selectionFilteredUsers = computed<UserData[]>(() => {
    let userFilter = this.selectionFilter();
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

  setUserAttribute(key: string, value: string) {
    const params: Record<string, string> = {
      user: this.detailsUsername(),
      realm: this.selectedUserRealm(),
      key,
      value
    };
    return this.http.post<PiResponse<number>>(this.baseUrl + "attribute", null, {
      headers: this.authService.getHeaders(),
      params
    });
  }

  deleteUserAttribute(key: string) {
    const username = this.detailsUsername();
    const realm = this.selectedUserRealm();
    const url =
      this.baseUrl +
      `attribute/${encodeURIComponent(key)}/${encodeURIComponent(username)}/${encodeURIComponent(realm)}`;
    return this.http.delete<PiResponse<any>>(url, { headers: this.authService.getHeaders() });
  }
}
