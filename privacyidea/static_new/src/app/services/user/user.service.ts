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
    }),
    computation: (source) => source.defaultRealm,
  });

  userNameFilter = linkedSignal({
    source: this.selectedUserRealm,
    computation: () => '',
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

  fetchedUsernames = computed<string[]>(() =>
    this.users().map((user) => user.username),
  );

  userOptions = computed(() => this.fetchedUsernames());

  filteredUserOptions = computed(() => {
    const filterValue = this.userNameFilter().toLowerCase();
    return this.userOptions().filter((option) =>
      option.toLowerCase().includes(filterValue),
    );
  });

  constructor(
    private localService: LocalService,
    private realmService: RealmService,
    private contentService: ContentService,
  ) {}
}
