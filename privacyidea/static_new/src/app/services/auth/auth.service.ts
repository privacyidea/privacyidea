import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { NotificationService } from '../notification/notification.service';
import { VersionService } from '../version/version.service';
import { PiResponse } from '../../app.component';

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
      .post<PiResponse<boolean>>(this.authUrl, JSON.stringify(params), {
        headers: new HttpHeaders({
          'Content-Type': 'application/json',
          Accept: 'application/json',
        }),
        withCredentials: true,
      })
      .pipe(
        tap((response: any) => {
          this.versionService.version.set(response.versionnumber);
          if (response?.result?.status) {
            this.acceptAuthentication();
            this.user.set(response.result.value.username);
            this.realm.set(response.result.value.realm);
            this.role.set(response.result.value.role);
            this.menus.set(response.result.value.menus);
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
