import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NotificationService } from '../../../../services/notification/notification.service';
import {
  EnrollmentResponse,
  EnrollmentResponseDetail,
  TokenService,
} from '../../../../services/token/token.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { from, Observable, switchMap, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-enroll-passkey',
  imports: [FormsModule, MatFormField, MatInput, MatLabel],
  templateUrl: './enroll-passkey.component.html',
  styleUrl: './enroll-passkey.component.scss',
})
export class EnrollPasskeyComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'passkey')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() enrollResponse!: WritableSignal<EnrollmentResponse | null>;
  @Input() firstDialog!: MatDialog;

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
  ) {}

  registerPasskey(detail: EnrollmentResponseDetail): Observable<any> {
    const options = detail.passkey_registration;

    const excludedCredentials = options.excludeCredentials.map((cred: any) => ({
      id: this.base64Service.base64URLToBytes(cred.id),
      type: cred.type,
    }));

    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      rp: options.rp,
      user: {
        id: this.base64Service.base64URLToBytes(options.user.id),
        name: options.user.name,
        displayName: options.user.displayName,
      },
      challenge: Uint8Array.from(options.challenge, (c: string) =>
        c.charCodeAt(0),
      ),
      pubKeyCredParams: options.pubKeyCredParams,
      excludeCredentials: excludedCredentials,
      authenticatorSelection: options.authenticatorSelection,
      timeout: options.timeout,
      extensions: {
        credProps: true,
      },
      attestation: options.attestation,
    };

    return from(
      navigator.credentials.create({ publicKey: publicKeyOptions }),
    ).pipe(
      // The any type is used here to avoid TypeScript errors, as the type of publicKeyCred is not strictly defined.
      switchMap((publicKeyCred: any) => {
        if (!publicKeyCred) {
          this.notificationService.openSnackBar(
            'No passkey was created, please try again.',
          );
          return throwError(() => new Error('No passkey created'));
        }
        const params: any = {
          type: 'passkey',
          transaction_id: detail.transaction_id,
          serial: detail.serial,
          credential_id: publicKeyCred.id,
          rawId: this.base64Service.bytesToBase64(
            new Uint8Array(publicKeyCred.rawId),
          ),
          authenticatorAttachment: publicKeyCred.authenticatorAttachment,
          attestationObject: this.base64Service.bytesToBase64(
            new Uint8Array(publicKeyCred.response.attestationObject),
          ),
          clientDataJSON: this.base64Service.bytesToBase64(
            new Uint8Array(publicKeyCred.response.clientDataJSON),
          ),
        };

        const extResults = publicKeyCred.getClientExtensionResults();
        if (extResults.credProps) {
          params.credProps = extResults.credProps;
        }

        return this.tokenService.enrollToken(params);
      }),
      catchError((error: any) => {
        console.error('Error while registering passkey', error);
        this.notificationService.openSnackBar(
          'Error while registering passkey, the token will not be created!',
        );
        return from(this.tokenService.deleteToken(detail.serial)).pipe(
          switchMap(() => {
            this.enrollResponse.set(null);
            this.firstDialog.closeAll();
            this.notificationService.openSnackBar(
              `Token ${detail.serial} deleted successfully.`,
            );
            return throwError(() => error);
          }),
        );
      }),
    );
  }
}
