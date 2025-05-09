import { computed, effect, Injectable, signal } from '@angular/core';
import { HttpErrorResponse, httpResource } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { LocalService } from '../local/local.service';
import { NotificationService } from '../notification/notification.service';
import { TokenService } from '../token/token.service';
import { ContainerService } from '../container/container.service';
import { AuthService } from '../auth/auth.service';

@Injectable({
  providedIn: 'root',
})
export class RealmService {
  selectedRealms = signal<string[]>([]);

  realmResource = httpResource<any>(() => {
    if (this.authService.role() === 'user') {
      return undefined;
    }
    return {
      url: environment.proxyUrl + '/realm/',
      method: 'GET',
      headers: this.localService.getHeaders(),
    };
  });
  realmOptions = computed(() => {
    this.tokenService.selectedTokenType();
    this.containerService.selectedContainerType();
    return Object.keys(this.realmResource.value()?.result?.value ?? []).map(
      (realm: string) => {
        return realm;
      },
    );
  });

  defaultRealmResource = httpResource<any>(() => {
    if (this.authService.role() === 'user') {
      return undefined;
    }
    return {
      url: environment.proxyUrl + '/defaultrealm',
      method: 'GET',
      headers: this.localService.getHeaders(),
    };
  });
  defaultRealm = computed<string>(() => {
    const data = this.defaultRealmResource.value();
    if (data?.result?.value) {
      return Object.keys(data.result.value)[0] ?? '';
    }
    return '';
  });

  constructor(
    private localService: LocalService,
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private containerService: ContainerService,
    private authService: AuthService,
  ) {
    effect(() => {
      if (this.realmResource.error()) {
        const realmError = this.realmResource.error() as HttpErrorResponse;
        console.error('Failed to get realms.', realmError.message);
        const message =
          realmError.error?.result?.error?.message || realmError.message;
        this.notificationService.openSnackBar(
          'Failed to get realms. ' + message,
        );
      }
    });

    effect(() => {
      if (this.defaultRealmResource.error()) {
        const defaultRealmError =
          this.defaultRealmResource.error() as HttpErrorResponse;
        console.error(
          'Failed to get default realm.',
          defaultRealmError.message,
        );
        const message =
          defaultRealmError.error?.result?.error?.message ||
          defaultRealmError.message;
        this.notificationService.openSnackBar(
          'Failed to get default realm. ' + message,
        );
      }
    });
  }
}
