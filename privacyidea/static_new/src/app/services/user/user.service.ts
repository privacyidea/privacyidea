import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { catchError, map } from 'rxjs/operators';
import { NotificationService } from '../notification/notification.service';
import { throwError } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class UserService {
  private baseUrl = environment.proxyUrl + '/user/';

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private notificationService: NotificationService,
  ) {}

  getUsers(userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .get(`${this.baseUrl}?realm=${userRealm}`, { headers })
      .pipe(
        map((response: any) => response.result),
        catchError((error) => {
          console.error('Failed to get users.', error);
          this.notificationService.openSnackBar('Failed to get users.');
          return throwError(() => error);
        }),
      );
  }
}
