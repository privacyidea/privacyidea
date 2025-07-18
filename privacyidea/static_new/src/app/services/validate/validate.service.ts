import { HttpClient } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { from, Observable, switchMap, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { PiResponse } from '../../app.component';
import {
  AuthResponse,
  AuthService,
  AuthServiceInterface,
} from '../auth/auth.service';
import {
  Base64Service,
  Base64ServiceInterface,
} from '../base64/base64.service';
import { LocalService, LocalServiceInterface } from '../local/local.service';
import {
  NotificationService,
  NotificationServiceInterface,
} from '../notification/notification.service';

export interface ValidateCheckDetail {
  attributes?: {
    hideResponseInput?: boolean;
  };
  client_mode?: 'poll' | 'push';
  message?: string;
  messages?: string[];
  multi_challenge?: {
    attributes?: {
      hideResponseInput?: boolean;
    };
    client_mode?: 'poll' | 'push';
    message?: string;
    serial?: string;
    transaction_id?: string;
    type?: 'push' | 'poll';
  }[];
  serial?: string;
  threadid?: number;
  transaction_id?: string;
  transaction_ids?: string[];
  type?: 'push' | 'poll';
  preferred_client_mode?: 'poll' | 'push';
}

export type ValidateCheckResponse = PiResponse<boolean, ValidateCheckDetail>;

export interface ValidateServiceInterface {
  testToken(
    tokenSerial: string,
    otpOrPinToTest: string,
    otponly?: string,
  ): Observable<ValidateCheckResponse>;
  authenticatePasskey(args?: { isTest?: boolean }): Observable<AuthResponse>;
}

@Injectable({
  providedIn: 'root',
})
export class ValidateService implements ValidateServiceInterface {
  private baseUrl = environment.proxyUrl + '/validate/';

  constructor(
    private http: HttpClient,
    @Inject(LocalService)
    private localService: LocalServiceInterface,
    @Inject(NotificationService)
    private notificationService: NotificationServiceInterface,
    @Inject(Base64Service)
    private base64Service: Base64ServiceInterface,
    @Inject(AuthService)
    private authenticationService: AuthServiceInterface,
  ) {}

  testToken(tokenSerial: string, otpOrPinToTest: string, otponly?: string) {
    const headers = this.localService.getHeaders();
    return this.http
      .post<ValidateCheckResponse>(
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

  authenticatePasskey(args?: { isTest?: boolean }) {
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
              ? this.http.post<AuthResponse>(`${this.baseUrl}check`, params)
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
