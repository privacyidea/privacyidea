import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { NotificationService } from '../notification/notification.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  isAuthenticated = false;
  private authUrl = environment.proxyUrl + '/auth';

  constructor(
    private http: HttpClient,
    private notificationService: NotificationService,
  ) {}

  authenticate(
    username: string,
    password: string,
    realm: string = '',
  ): Observable<{
    result: { status: boolean };
  }> {
    const loginData = { username, password, realm };

    return this.http
      .post(this.authUrl, JSON.stringify(loginData), {
        headers: new HttpHeaders({
          'Content-Type': 'application/json',
          Accept: 'application/json',
        }),
        withCredentials: true,
      })
      .pipe(
        tap((response: any) => {
          if (response?.result?.status) {
            this.isAuthenticated = true;
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
    return this.isAuthenticated;
  }

  deauthenticate(): void {
    this.isAuthenticated = false;
  }
}
