import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { catchError } from 'rxjs/operators';
import { from, Observable, switchMap, throwError } from 'rxjs';
import { NotificationService } from '../notification/notification.service';
import { Base64Service } from '../base64/base64.service';
import { AuthService } from '../auth/auth.service';

@Injectable({
  providedIn: 'root',
})
export class ValidateService {
  private baseUrl = environment.proxyUrl + '/validate/';

  constructor(
    private http: HttpClient,
    private localService: LocalService,
    private notificationService: NotificationService,
    private base64Service: Base64Service,
    private authenticationService: AuthService,
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

  authenticatePasskey(args?: { isTest?: boolean }): Observable<any> {
    if (!window.PublicKeyCredential) {
      this.notificationService.openSnackBar(
        'WebAuthn is not supported by this browser.',
      );
      return throwError(
        () => new Error('WebAuthn is not supported by this browser.'),
      );
    }
    return from(PublicKeyCredential.isConditionalMediationAvailable()).pipe(
      switchMap(() => {
        return this.http.post<any>(`${this.baseUrl}initialize`, {
          type: 'passkey',
        });
      }),
      switchMap((initResponse: any) => {
        const data = initResponse.detail.passkey;
        let userVerification: UserVerificationRequirement = 'required';
        return from(
          navigator.credentials.get({
            publicKey: {
              challenge: Uint8Array.from(data.challenge, (c: string) =>
                c.charCodeAt(0),
              ),
              rpId: data.rpId,
              userVerification: userVerification,
            },
          }),
        ).pipe(
          switchMap((credential: any) => {
            const params = {
              transaction_id: data.transaction_id,
              credential_id: credential.id,
              authenticatorData: this.base64Service.bytesToBase64(
                new Uint8Array(credential.response.authenticatorData),
              ),
              clientDataJSON: this.base64Service.bytesToBase64(
                new Uint8Array(credential.response.clientDataJSON),
              ),
              signature: this.base64Service.bytesToBase64(
                new Uint8Array(credential.response.signature),
              ),
              userHandle: this.base64Service.bytesToBase64(
                new Uint8Array(credential.response.userHandle),
              ),
            };
            return args?.isTest
              ? this.http.post(`${this.baseUrl}check`, params)
              : this.authenticationService.authenticate(params);
          }),
        );
      }),
      catchError((error: any) => {
        console.error('Error during passkey authentication', error);
        const errorMessage =
          error.error?.result?.error?.message ||
          error.message ||
          'Error during authentication';
        this.notificationService.openSnackBar(errorMessage);
        return throwError(() => new Error(errorMessage));
      }),
    );
  }
}
