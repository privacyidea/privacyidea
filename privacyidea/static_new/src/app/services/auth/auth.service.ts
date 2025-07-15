import { HttpClient, HttpHeaders } from '@angular/common/http';
import { computed, Inject, Injectable, signal } from '@angular/core';
import { throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../notification/notification.service';
import { VersionService } from '../version/version.service';

export type AuthResponse = PiResponse<AuthData, AuthDetail>;

export interface AuthData {
  log_level: number;
  menus: string[];
  realm: string;
  rights: string[];
  role: AuthRole;
  token: string;
  username: string;
  logout_time: number;
  audit_page_size: number;
  token_page_size: number;
  user_page_size: number;
  policy_template_url: string;
  default_tokentype: string;
  default_container_type: string;
  user_details: boolean;
  token_wizard: boolean;
  token_wizard_2nd: boolean;
  admin_dashboard: boolean;
  dialog_no_token: boolean;
  search_on_enter: boolean;
  timeout_action: string;
  token_rollover: any;
  hide_welcome: boolean;
  hide_buttons: boolean;
  deletion_confirmation: boolean;
  show_seed: boolean;
  show_node: string;
  subscription_status: number;
  subscription_status_push: number;
  qr_image_android: string | null;
  qr_image_ios: string | null;
  qr_image_custom: string | null;
  logout_redirect_url: string;
  require_description: string[];
  rss_age: number;
  container_wizard: {
    enabled: boolean;
  };
}

export type AuthRole = 'admin' | 'user' | '';

export interface AuthDetail {
  username: string;
}

export interface AuthServiceInterface {
  isAuthenticated: () => boolean;
  user: () => string;
  realm: () => string;
  role: () => AuthRole;
  menus: () => string[];
  isSelfServiceUser: () => boolean;
  authenticate: (params: any) => any;
  isAuthenticatedUser: () => boolean;
  acceptAuthentication: () => void;
  deauthenticate: () => void;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService implements AuthServiceInterface {
  readonly authUrl = environment.proxyUrl + '/auth';
  isAuthenticated = signal(false);
  user = signal('');
  realm = signal('');
  role = signal<AuthRole>('');
  menus = signal<string[]>([]);

  isSelfServiceUser = computed(() => {
    return this.role() === 'user';
  });

  constructor(
    readonly http: HttpClient,
    @Inject(NotificationService)
    readonly notificationService: NotificationServiceInterface,
    readonly versionService: VersionService,
  ) {}

  authenticate(params: any) {
    return this.http
      .post<AuthResponse>(this.authUrl, JSON.stringify(params), {
        headers: new HttpHeaders({
          'Content-Type': 'application/json',
          Accept: 'application/json',
        }),
        withCredentials: true,
      })
      .pipe(
        tap((response) => {
          this.versionService.version.set(response.versionnumber);
          const value = response.result?.value;
          if (response?.result?.status && value) {
            this.acceptAuthentication();
            this.user.set(value.username);
            this.realm.set(value.realm);
            this.role.set(value.role);
            this.menus.set(value.menus);
          }
        }),
        catchError((error) => {
          console.error('Login failed.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar('Login failed. ' + message);
          return throwError(() => error);
        }),
      );
  }

  isAuthenticatedUser(): boolean {
    return this.isAuthenticated();
  }

  acceptAuthentication(): void {
    this.isAuthenticated.set(true);
  }

  deauthenticate(): void {
    this.isAuthenticated.set(false);
  }
}
