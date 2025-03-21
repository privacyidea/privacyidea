import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';
import { NotificationService } from '../notification/notification.service';
import { Base64Service } from '../base64/base64.service';

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

  authenticatePasskey(): void {
    if (window.PublicKeyCredential) {
      PublicKeyCredential.isConditionalMediationAvailable().then(() => {
        this.http
          .post<any>(`${this.baseUrl}initialize`, {
            type: 'passkey',
          })
          .subscribe({
            next: (initResponse: any) => {
              const data = initResponse.detail.passkey;
              let userVerification: UserVerificationRequirement = 'preferred';
              if (
                ['required', 'preferred', 'discouraged'].includes(
                  data.user_verification,
                )
              ) {
                userVerification = data.user_verification;
              }

              navigator.credentials
                .get({
                  publicKey: {
                    challenge: Uint8Array.from(data.challenge, (c: string) =>
                      c.charCodeAt(0),
                    ),
                    rpId: data.rpId,
                    userVerification: userVerification,
                  },
                })
                .then((credential: any) => {
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

                  this.http.post(`${this.baseUrl}check`, params, {}).subscribe({
                    next: (checkResponse: any) => {
                      if (checkResponse.result.value) {
                        this.notificationService.openSnackBar(
                          'Test successful. You would have been logged in as: ' +
                            checkResponse.detail.username,
                        );
                      } else {
                        this.notificationService.openSnackBar('No user found.');
                      }
                    },
                    error: (err: any) => {
                      console.error('Error during check', err);
                      this.notificationService.openSnackBar(
                        err.error?.result?.error?.message ||
                          'Error during check',
                      );
                    },
                  });
                })
                .catch((credError: any) => {
                  console.error('Error obtaining credentials', credError);
                  this.notificationService.openSnackBar(
                    credError.error?.result?.error?.message ||
                      'Error obtaining credentials',
                  );
                });
            },
            error: (initError: any) => {
              console.error('Error during initialization', initError);
              this.notificationService.openSnackBar(
                initError.error?.result?.error?.message ||
                  'Error during initialization',
              );
            },
          });
      });
    } else {
      this.notificationService.openSnackBar(
        'WebAuthn is not supported by this browser.',
      );
    }
  }
}
