import {
  computed,
  Injectable,
  linkedSignal,
  WritableSignal,
} from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { RealmService } from '../realm/realm.service';
import { ContentService } from '../content/content.service';
import { PiResponse } from '../../app.component';
import { TokenService } from '../token/token.service';
import { AuthService } from '../auth/auth.service';

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

@Injectable({
  providedIn: 'root',
})
export class UserService {
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
      console.log('UserService.selectedUserRealm computation', source);
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
    computation: () => {
      console.log('UserService.userFilter computation');
      return '';
    },
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

  constructor(
    private localService: LocalService,
    private realmService: RealmService,
    private contentService: ContentService,
    private tokenService: TokenService,
    private authService: AuthService,
  ) {}
}
