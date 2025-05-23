import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { NotificationService } from '../notification/notification.service';
import { VersionService } from '../version/version.service';
import { PiResponse } from '../../app.component';

export interface AuthData {
  log_level: number;
  menus: string[];
  realm: string;
  rights: string[];
  role: string;
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
@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private authUrl = environment.proxyUrl + '/auth';
  isAuthenticated = signal(false);
  user = signal('');
  realm = signal('');
  role = signal('');
  menus = signal<string[]>([]);

  constructor(
    private http: HttpClient,
    private notificationService: NotificationService,
    private versionService: VersionService,
  ) {}

  authenticate(params: any) {
    return this.http
      .post<PiResponse<AuthData>>(this.authUrl, JSON.stringify(params), {
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
