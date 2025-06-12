import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { from, Observable, switchMap, throwError } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';
import { catchError } from 'rxjs/operators';

// Interface für die Initialisierungsoptionen des WebAuthn Tokens (erster Schritt)
export interface WebauthnEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'webauthn';
  // Keine zusätzlichen typspezifischen Felder für den *ersten* Enrollment-Aufruf (init)
  // Die komplexeren Daten werden im zweiten Schritt nach der Browser-Interaktion gesendet.
}

// Interface für die Parameter des *zweiten* Enrollment-Aufrufs (nach Browser-Interaktion)
export interface WebauthnRegistrationParams {
  type: 'webauthn';
  transaction_id: string;
  serial: string;
  credential_id: string; // ArrayBuffer
  rawId: string; // base64
  authenticatorAttachment: string | null;
  regdata: string; // base64 (attestationObject)
  clientdata: string; // base64 (clientDataJSON)
  credProps?: any;
}

@Component({
  selector: 'app-enroll-webauthn',
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-webauthn.component.html',
  styleUrl: './enroll-webauthn.component.scss',
})
export class EnrollWebauthnComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'webauthn')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() enrollResponse!: WritableSignal<any>;
  @Input() firstDialog!: MatDialog;

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
  ) {}

  registerWebauthn(detail: any): Observable<any> {
    if (!navigator.credentials?.create) {
      const errorMsg = 'WebAuthn is not supported by this browser.';
      this.notificationService.openSnackBar(errorMsg);
      return throwError(() => new Error(errorMsg));
    }

    const request = detail.webAuthnRegisterRequest;
    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      rp: {
        id: request.relyingParty?.id, // Optional chaining für Sicherheit
        name: request.relyingParty.name,
      },
      user: {
        id: new TextEncoder().encode(request.serialNumber),
        name: request.name,
        displayName: request.displayName,
      },
      challenge: this.base64Service.base64URLToBytes(request.nonce),
      pubKeyCredParams: request.pubKeyCredAlgorithms,
      timeout: request.timeout,
      excludeCredentials: request.excludeCredentials
        ? request.excludeCredentials.map((cred: any) => ({
            id: this.base64Service.base64URLToBytes(cred.id),
            type: cred.type,
            transports: cred.transports,
          }))
        : [],
      authenticatorSelection: request.authenticatorSelection,
      attestation: request.attestation,
      extensions: request.extensions,
    };

    return from(
      navigator.credentials.create({ publicKey: publicKeyOptions }),
    ).pipe(
      switchMap((publicKeyCred: any) => {
        const params: any = {
          type: 'webauthn',
          transaction_id: request.transaction_id,
          serial: request.serialNumber,
          credential_id: publicKeyCred.id,
          rawId: this.base64Service.bytesToBase64(
            new Uint8Array(publicKeyCred.rawId),
          ),
          authenticatorAttachment: publicKeyCred.authenticatorAttachment,
          regdata: this.base64Service.bytesToBase64(
            new Uint8Array(publicKeyCred.response.attestationObject),
          ),
          clientdata: this.base64Service.bytesToBase64(
            new Uint8Array(publicKeyCred.response.clientDataJSON),
          ),
        };

        const extResults = publicKeyCred.getClientExtensionResults();
        if (extResults.credProps) {
          params.credProps = extResults.credProps;
        }

        return this.tokenService.enrollToken(params);
      }),
      catchError((error) => {
        this.enrollResponse.set(null);
        this.firstDialog.closeAll();
        const errMsg = `Error during WebAuthn registration: ${error.message || error}`;
        this.notificationService.openSnackBar(errMsg);
        return throwError(() => error);
      }),
    );
  }
}
