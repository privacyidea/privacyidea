import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';
import { NotificationService } from '../notification/notification.service';

@Injectable({
  providedIn: 'root',
})
export class ValidateService {
  private baseUrl = environment.proxyUrl + '/validate/';

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private notificationService: NotificationService,
  ) {}

  testToken(
    tokenSerial: string,
    otpOrPinToTest: string,
    otponly?: string,
  ): any {
    const headers = this.localService.getHeaders();
    return this.http
      .post(
        `${this.baseUrl}check`,
        {
          serial: tokenSerial,
          pass: otpOrPinToTest,
          otponly: otponly,
        },
        { headers },
      )
      .pipe(
        catchError((error: any) => {
          console.error('Failed to test token.', error);
          const message = error.error?.result?.error?.message || '';
          this.notificationService.openSnackBar(
            'Failed to test token. ' + message,
          );
          return throwError(() => error);
        }),
      );
  }
}
