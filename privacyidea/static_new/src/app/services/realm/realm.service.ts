import { computed, effect, Injectable, signal } from '@angular/core';
import { HttpErrorResponse, httpResource } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { LocalService } from '../local/local.service';
import { NotificationService } from '../notification/notification.service';
import { AuthService } from '../auth/auth.service';
import { PiResponse } from '../../app.component';

export type Realms = Map<string, Realm>;

export interface Realm {
  default: boolean;
  id: number;
  option: string;
  resolver: RealmResolvers;
}

export type RealmResolvers = Array<RealmResolver>;

export interface RealmResolver {
  name: string;
  node: string;
  type: string;
  priority: any;
}

@Injectable({
  providedIn: 'root',
})
export class RealmService {
  selectedRealms = signal<string[]>([]);

  realmResource = httpResource<PiResponse<Realms>>(() => {
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
    const realms = this.realmResource.value()?.result?.value;
    return realms ? Object.keys(realms) : [];
  });

  defaultRealmResource = httpResource<PiResponse<Realms>>(() => {
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
