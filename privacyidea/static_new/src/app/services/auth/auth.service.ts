import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { NotificationService } from '../notification/notification.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  isAuthenticated = signal(false);
  user = signal('');
  realm = signal('');
  role = signal('');
  private authUrl = environment.proxyUrl + '/auth';

  constructor(
    private http: HttpClient,
    private notificationService: NotificationService,
  ) {}

  authenticate(params: any): Observable<{
    result: { status: boolean };
  }> {
    return this.http
      .post(this.authUrl, JSON.stringify(params), {
        headers: new HttpHeaders({
          'Content-Type': 'application/json',
          Accept: 'application/json',
        }),
        withCredentials: true,
      })
      .pipe(
        tap((response: any) => {
          if (response?.result?.status) {
            this.acceptAuthentication();
            this.user.set(response.result.value.username);
            this.realm.set(response.result.value.realm);
            this.role.set(response.result.value.role);
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
