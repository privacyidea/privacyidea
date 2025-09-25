/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { from, map, Observable, switchMap, throwError } from "rxjs";
import { catchError } from "rxjs/operators";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthResponse, AuthService, AuthServiceInterface } from "../auth/auth.service";
import { Base64Service, Base64ServiceInterface } from "../base64/base64.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";

export interface ValidateCheckDetail {
  attributes?: {
    hideResponseInput?: boolean;
  };
  client_mode?: "poll" | "push";
  message?: string;
  messages?: string[];
  multi_challenge?: {
    attributes?: {
      hideResponseInput?: boolean;
    };
    client_mode?: "poll" | "push";
    message?: string;
    serial?: string;
    transaction_id?: string;
    type?: "push" | "poll";
  }[];
  serial?: string;
  threadid?: number;
  transaction_id?: string;
  transaction_ids?: string[];
  type?: "push" | "poll";
  preferred_client_mode?: "poll" | "push";
}

export type ValidateCheckResponse = PiResponse<boolean, ValidateCheckDetail>;

export interface ValidateServiceInterface {
  testToken(tokenSerial: string, otpOrPinToTest: string, otponly?: string): Observable<ValidateCheckResponse>;

  authenticatePasskey(args?: { isTest?: boolean }): Observable<AuthResponse>;

  authenticateWebAuthn(args: {
    signRequest: any;
    transaction_id: string;
    username: string;
    isTest?: boolean;
  }): Observable<AuthResponse>;

  pollTransaction(transactionId: string): Observable<boolean>;
}

@Injectable({
  providedIn: "root"
})
export class ValidateService implements ValidateServiceInterface {
  private readonly http: HttpClient = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  private readonly authenticationService: AuthServiceInterface = inject(AuthService);

  private baseUrl = environment.proxyUrl + "/validate/";

  testToken(tokenSerial: string, otpOrPinToTest: string, otponly?: string): Observable<ValidateCheckResponse> {
    const headers = this.authService.getHeaders();
    return this.http
      .post<ValidateCheckResponse>(
        `${this.baseUrl}check`,
        {
          serial: tokenSerial,
          pass: otpOrPinToTest,
          otponly: otponly
        },
        { headers }
      )
      .pipe(
        catchError((error: any) => {
          console.error("Failed to test token.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to test token. " + message);
          return throwError(() => error);
        })
      );
  }

  authenticatePasskey(args?: { isTest?: boolean }): Observable<AuthResponse> {
    if (!window.PublicKeyCredential) {
      this.notificationService.openSnackBar("WebAuthn is not supported by this browser.");
      return throwError(() => new Error("WebAuthn is not supported by this browser."));
    }
    return from(PublicKeyCredential.isConditionalMediationAvailable()).pipe(
      switchMap(() => {
        return this.http.post<any>(`${this.baseUrl}initialize`, {
          type: "passkey"
        });
      }),
      switchMap((initResponse: any) => {
        const data = initResponse.detail.passkey;
        let userVerification: UserVerificationRequirement = "required";
        return from(
          navigator.credentials.get({
            publicKey: {
              challenge: Uint8Array.from(data.challenge, (c: string) => c.charCodeAt(0)),
              rpId: data.rpId,
              userVerification: userVerification
            }
          })
        ).pipe(
          switchMap((credential: any) => {
            const params = {
              transaction_id: data.transaction_id,
              credential_id: credential.id,
              authenticatorData: this.base64Service.bytesToBase64(
                new Uint8Array(credential.response.authenticatorData)
              ),
              clientDataJSON: this.base64Service.bytesToBase64(new Uint8Array(credential.response.clientDataJSON)),
              signature: this.base64Service.bytesToBase64(new Uint8Array(credential.response.signature)),
              userHandle: this.base64Service.bytesToBase64(new Uint8Array(credential.response.userHandle))
            };
            return args?.isTest
              ? this.http.post<AuthResponse>(`${this.baseUrl}check`, params)
              : this.authenticationService.authenticate(params);
          })
        );
      }),
      catchError((error: any) => {
        console.error("Error during passkey authentication", error);
        const errorMessage = error.error?.result?.error?.message || error.message || "Error during authentication";
        this.notificationService.openSnackBar(errorMessage);
        return throwError(() => new Error(errorMessage));
      })
    );
  }

  authenticateWebAuthn(args: {
    signRequest: any;
    transaction_id: string;
    username: string;
    isTest?: boolean;
  }): Observable<AuthResponse> {
    if (!window.PublicKeyCredential) {
      this.notificationService.openSnackBar("WebAuthn is not supported by this browser.");
      return throwError(() => new Error("WebAuthn is not supported by this browser."));
    }

    try {
      const signRequest = args.signRequest;

      const publicKey: any = {
        challenge: this.base64Service.webAuthnBase64DecToArr(signRequest.challenge),
        allowCredentials: signRequest.allowCredentials.map((cred: any) => ({
          ...cred,
          id: this.base64Service.webAuthnBase64DecToArr(cred.id)
        })),
        rpId: signRequest.rpId,
        userVerification: signRequest.userVerification,
        timeout: signRequest.timeout
      };

      return from(navigator.credentials.get({ publicKey })).pipe(
        switchMap((credential: any) => {
          const finalParams = {
            transaction_id: args.transaction_id,
            username: args.username,
            credential_id: credential.id, // This is already base64url encoded
            authenticatorData: this.base64Service.webAuthnBase64EncArr(credential.response.authenticatorData),
            clientDataJSON: this.base64Service.webAuthnBase64EncArr(credential.response.clientDataJSON),
            signature: this.base64Service.webAuthnBase64EncArr(credential.response.signature),
            userHandle: credential.response.userHandle
              ? this.base64Service.utf8ArrToStr(credential.response.userHandle)
              : null
          };

          return args?.isTest
            ? this.http.post<AuthResponse>(`${this.baseUrl}check`, finalParams)
            : this.authenticationService.authenticate(finalParams);
        }),
        catchError((error: any) => {
          console.error("Error during WebAuthn authentication", error);
          const errorMessage =
            error.error?.result?.error?.message || error.message || "Error during WebAuthn authentication";
          this.notificationService.openSnackBar(errorMessage);
          return throwError(() => new Error(errorMessage));
        })
      );
    } catch (e) {
      const message = "Invalid WebAuthn challenge data received from server.";
      console.error(message, e);
      this.notificationService.openSnackBar(message);
      return throwError(() => new Error(message));
    }
  }

  pollTransaction(transactionId: string): Observable<boolean> {
    const headers = this.authService.getHeaders();
    return this.http
      .get<PiResponse<boolean, any>>(`${this.baseUrl}polltransaction`, {
        params: {
          transaction_id: transactionId
        },
        headers
      })
      .pipe(
        map((response) => {
          return response.result?.authentication === "ACCEPT" && response.result?.value === true;
        }),
        catchError((error: any) => {
          console.error("Failed to poll transaction.", error);
          const message = error.error?.result?.error?.message || "Polling for transaction failed.";
          this.notificationService.openSnackBar(message);
          return throwError(() => error);
        })
      );
  }
}
