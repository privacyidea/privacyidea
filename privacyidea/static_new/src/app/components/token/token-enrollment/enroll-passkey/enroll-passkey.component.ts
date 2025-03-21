import { Component, Input, WritableSignal } from '@angular/core';
import { TokenComponent } from '../../token.component';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { NotificationService } from '../../../../services/notification/notification.service';
import { TokenService } from '../../../../services/token/token.service';
import { Base64Service } from '../../../../services/base64/base64.service';

@Component({
  selector: 'app-enroll-passkey',
  imports: [FormsModule, MatFormField, MatInput, MatLabel],
  templateUrl: './enroll-passkey.component.html',
  styleUrl: './enroll-passkey.component.scss',
})
export class EnrollPasskeyComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'passkey')?.text;
  @Input() description!: WritableSignal<string>;
  private static notificationService: NotificationService;
  private static tokenService: TokenService;
  private static base64Service: Base64Service;

  static registerPasskey(detail: any): void {
    const options = detail.passkeyOptions;

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

    navigator.credentials
      .create({ publicKey: publicKeyOptions })
      .then((publicKeyCred: any) => {
        const params: any = {
          user: detail.newUser?.user,
          realm: detail.newUser?.realm,
          transaction_id: detail.transaction_id,
          serial: detail.serial,
          type: 'passkey',
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

        this.tokenService.enrollToken(params).subscribe();
      })
      .catch((error: any) => {
        console.error('Error while registering passkey', error);
        this.notificationService.openSnackBar(
          'Error while registering passkey, the token will not be created!',
        );
        this.tokenService.deleteToken(detail.serial).subscribe({
          next: () => {
            this.notificationService.openSnackBar(
              `Token ${detail.serial} deleted successfully.`,
            );
          },
        });
      });
  }
}
