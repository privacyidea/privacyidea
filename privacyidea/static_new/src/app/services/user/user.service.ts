import { computed, Injectable, linkedSignal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { TokenService } from '../token/token.service';
import { ContainerService } from '../container/container.service';
import { RealmService } from '../realm/realm.service';

@Injectable({
  providedIn: 'root',
})
export class UserService {
  private baseUrl = environment.proxyUrl + '/user/';

  selectedUserRealm = linkedSignal({
    source: () => ({
      selectedContent: this.tokenService.selectedContent(),
      tokenServiceSelectedType: this.tokenService.selectedTokenType(),
      containerServiceSelectedType:
        this.containerService.selectedContainerType(),
      defaultRealm: this.realmService.defaultRealm(),
    }),
    computation: (source: any) => source.defaultRealm ?? '',
  });

  selectedUsername = linkedSignal({
    source: () => ({
      tokenServiceSelectedType: this.tokenService.selectedTokenType(),
      containerServiceSelectedType:
        this.containerService.selectedContainerType(),
    }),
    computation: () => '',
  });

  userResource = httpResource<any>(() => {
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
  fetchedUsernames = computed<string[]>(() => {
    const data = this.userResource.value();
    if (!data?.result?.value) {
      return [];
    }
    return data.result.value.map((user: any) => user.username);
  });

  userOptions = computed(() => this.fetchedUsernames());

  filteredUserOptions = computed(() => {
    const filterValue = (this.selectedUsername() || '').toLowerCase();
    return this.userOptions().filter((option: any) =>
      option.toLowerCase().includes(filterValue),
    );
  });

  constructor(
    private localService: LocalService,
    private tokenService: TokenService,
    private containerService: ContainerService,
    private realmService: RealmService,
  ) {}
}
