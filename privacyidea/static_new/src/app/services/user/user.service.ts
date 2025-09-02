import { httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, inject, Injectable, linkedSignal, signal, Signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { RealmService, RealmServiceInterface } from "../realm/realm.service";
import { TokenService, TokenServiceInterface } from "../token/token.service";

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
  selectedUserRealm: WritableSignal<string>;
  selectedUser: Signal<UserData | null>;
  userFilter: WritableSignal<string | UserData | null>;
  userNameFilter: Signal<string>;
  userResource: HttpResourceRef<PiResponse<UserData[]> | undefined>;
  user: WritableSignal<UserData>;
  usersResource: HttpResourceRef<PiResponse<UserData[]> | undefined>;
  users: WritableSignal<UserData[]>;
  allUsernames: Signal<string[]>;
  filteredUsernames: Signal<string[]>;
  filteredUsers: Signal<UserData[]>;
  filterValue: WritableSignal<Record<string, string>>;
  pageIndex: WritableSignal<number>;
  pageSize: WritableSignal<number>;
  apiFilter: string[];
  advancedApiFilter: string[];

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
  readonly apiFilter = apiFilter;
  readonly advancedApiFilter = advancedApiFilter;
  private baseUrl = environment.proxyUrl + "/user/";
  filterValue = signal({} as Record<string, string>);
  filterParams = computed<Record<string, string>>(() => {
    const allowedFilters = [...this.apiFilter, ...this.advancedApiFilter];
    const filterPairs = Object.entries(this.filterValue())
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
  pageSize = linkedSignal({
    source: this.filterValue,
    computation: () => 10
  });
  pageIndex = linkedSignal({
    source: () => ({
      filterValue: this.filterValue(),
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
  userFilter = linkedSignal<string, UserData | string>({
    source: this.selectedUserRealm,
    computation: () => ""
  });
  userNameFilter = computed<string>(() => {
    const filter = this.userFilter();
    if (typeof filter === "string") {
      return filter;
    }
    return filter?.username ?? "";
  });
  userResource = httpResource<PiResponse<UserData[]>>(() => {
    if (this.authService.role() !== "user") {
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
      this.authService.role() === "user" ||
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
  sort = signal({ active: "serial", direction: "asc" } as Sort);
  users: WritableSignal<UserData[]> = linkedSignal({
    source: this.usersResource.value,
    computation: (source, previous) => source?.result?.value ?? previous?.value ?? []
  });
  selectedUser = computed<UserData | null>(() => {
    var userName = "";
    if (this.authService.role() === "user") {
      userName = this.authService.username();
    } else {
      userName = this.userNameFilter();
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
  filteredUsers = computed<UserData[]>(() => {
    var userFilter = this.userFilter();
    if (typeof userFilter !== "string" || userFilter.trim() === "") {
      return this.users();
    }
    const filterValue = userFilter.toLowerCase().trim();
    return this.users().filter((user) => user.username.toLowerCase().includes(filterValue));
  });
  filteredUsernames = computed<string[]>(() => this.filteredUsers().map((user) => user.username));

  displayUser(user: UserData | string): string {
    if (typeof user === "string") {
      return user;
    }
    return user ? user.username : "";
  }
}
