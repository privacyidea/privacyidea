import { httpResource, HttpResourceRef } from '@angular/common/http';
import {
  computed,
  inject,
  Injectable,
  linkedSignal,
  Signal,
  WritableSignal,
} from '@angular/core';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import { AuthService, AuthServiceInterface } from '../auth/auth.service';
import {
  ContentService,
  ContentServiceInterface,
} from '../content/content.service';
import { LocalService, LocalServiceInterface } from '../local/local.service';
import { RealmService, RealmServiceInterface } from '../realm/realm.service';
import { TokenService, TokenServiceInterface } from '../token/token.service';

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
  userFilter: WritableSignal<string | UserData>;
  userNameFilter: Signal<string>;
  userResource: HttpResourceRef<PiResponse<UserData[]> | undefined>;
  user: WritableSignal<UserData>;
  usersResource: HttpResourceRef<PiResponse<UserData[]> | undefined>;
  users: WritableSignal<UserData[]>;
  allUsernames: Signal<string[]>;
  usersOfRealmResource: HttpResourceRef<PiResponse<UserData[]> | undefined>;
  filteredUsernames: Signal<string[]>;
  filteredUsers: Signal<UserData[]>;
  displayUser(user: UserData | string): string;
}

@Injectable({
  providedIn: 'root',
})
export class UserService implements UserServiceInterface {
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly contentService: ContentServiceInterface =
    inject(ContentService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly authService: AuthServiceInterface = inject(AuthService);

  private baseUrl = environment.proxyUrl + '/user/';

  selectedUserRealm = linkedSignal({
    source: () => ({
      selectedContent: this.contentService.selectedContent(),
      defaultRealm: this.realmService.defaultRealm(),
      selectedTokenType: this.tokenService.selectedTokenType(),
      authRole: this.authService.role(),
      authRealm: this.authService.realm(),
    }),
    computation: (source) => {
      if (source.authRole === 'user') {
        return source.authRealm;
      }
      return source.defaultRealm;
    },
  });

  selectedUser = computed<UserData | null>(() => {
    var userName = '';
    if (this.authService.role() === 'user') {
      userName = this.authService.user();
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

  userFilter = linkedSignal<string, UserData | string>({
    source: this.selectedUserRealm,
    computation: () => '',
  });

  userNameFilter = computed<string>(() => {
    const filter = this.userFilter();
    if (typeof filter === 'string') {
      return filter;
    }
    return filter?.username ?? '';
  });

  userResource = httpResource<PiResponse<UserData[]>>(() => {
    return {
      url: this.baseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
    };
  });

  user: WritableSignal<UserData> = linkedSignal({
    source: this.userResource.value,
    computation: (source, previous) => {
      return (
        source?.result?.value?.[0] ??
        previous?.value ?? {
          description: '',
          editable: false,
          email: '',
          givenname: '',
          mobile: '',
          phone: '',
          resolver: '',
          surname: '',
          userid: '',
          username: '',
        }
      );
    },
  });

  usersResource = httpResource<PiResponse<UserData[]>>(() => {
    const selectedUserRealm = this.selectedUserRealm();
    if (selectedUserRealm === '') {
      return undefined;
    }
    return {
      url: this.baseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: {
        realm: selectedUserRealm,
      },
    };
  });

  users: WritableSignal<UserData[]> = linkedSignal({
    source: this.usersResource.value,
    computation: (source, previous) =>
      source?.result?.value ?? previous?.value ?? [],
  });

  allUsernames = computed<string[]>(() =>
    this.users().map((user) => user.username),
  );

  usersOfRealmResource = httpResource<PiResponse<UserData[]>>(() => {
    const selectedUserRealm = this.selectedUserRealm();
    if (selectedUserRealm === '') {
      return undefined;
    }
    return {
      url: this.baseUrl,
      method: 'GET',
      headers: this.localService.getHeaders(),
      params: {
        realm: selectedUserRealm,
      },
    };
  });

  filteredUsernames = computed<string[]>(() =>
    this.filteredUsers().map((user) => user.username),
  );

  filteredUsers = computed<UserData[]>(() => {
    var userFilter = this.userFilter();
    if (typeof userFilter !== 'string' || userFilter.trim() === '') {
      return this.users();
    }
    const filterValue = userFilter.toLowerCase().trim();
    const filteredUsers = this.users().filter((user) =>
      user.username.toLowerCase().includes(filterValue),
    );
    return filteredUsers;
  });

  displayUser(user: UserData | string): string {
    if (typeof user === 'string') {
      return user;
    }
    return user ? user.username : '';
  }
}
