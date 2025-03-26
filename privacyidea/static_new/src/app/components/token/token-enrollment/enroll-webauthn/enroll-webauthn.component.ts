import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { Observable } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-enroll-webauthn',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-webauthn.component.html',
  styleUrl: './enroll-webauthn.component.scss',
})
export class EnrollWebauthnComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'webauthn')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() response!: WritableSignal<any>;
  @Input() firstDialog!: MatDialog;

  constructor(
    private notificationService: NotificationService,
    private base64Service: Base64Service,
  ) {}

  registerWebauthn(detail: any): Observable<any> {
    return new Observable((subscriber) => {
      if (!navigator.credentials || !navigator.credentials.create) {
        const errorMsg = 'WebAuthn is not supported by this browser.';
        this.notificationService.openSnackBar(errorMsg);
        subscriber.error(errorMsg);
        return;
      }
      try {
        const request = detail.webAuthnRegisterRequest;
        const publicKey: PublicKeyCredentialCreationOptions = {
          rp: {
            id: request.relyingParty.id,
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
        navigator.credentials
          .create({ publicKey })
          .then((credential: Credential | null) => {
            if (!credential) {
              subscriber.error('No credential returned from WebAuthn.');
              return;
            }
            const publicKeyCredential = credential as PublicKeyCredential;
            const response =
              publicKeyCredential.response as AuthenticatorAttestationResponse;
            const result = {
              id: publicKeyCredential.id,
              rawId: this.base64Service.bufferToBase64Url(
                new Uint8Array(publicKeyCredential.rawId),
              ),
              type: publicKeyCredential.type,
              response: {
                attestationObject: this.base64Service.bufferToBase64Url(
                  new Uint8Array(response.attestationObject),
                ),
                clientDataJSON: this.base64Service.bufferToBase64Url(
                  new Uint8Array(response.clientDataJSON),
                ),
              },
            };
            subscriber.next();
            subscriber.complete();
          })
          .catch((error: any) => {
            this.response.set(null);
            this.firstDialog.closeAll();
            const errMsg = `Error during WebAuthn registration: ${error.message || error}`;
            this.notificationService.openSnackBar(errMsg);
            subscriber.error(error);
          });
      } catch (err: any) {
        const errMsg = `Error in WebAuthn registration setup: ${err.message || err}`;
        this.notificationService.openSnackBar(errMsg);
        subscriber.error(err);
      }
    });
  }
}
