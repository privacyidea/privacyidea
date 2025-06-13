import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { NotificationService } from '../../../../services/notification/notification.service';
import { Base64Service } from '../../../../services/base64/base64.service';
import { from, Observable, switchMap, throwError, of } from 'rxjs';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import {
  BasicEnrollmentOptions,
  EnrollmentResponse,
  TokenService,
} from '../../../../services/token/token.service';
import { catchError, finalize, tap } from 'rxjs/operators';
import { TokenEnrollmentFirstStepDialogComponent } from '../token-enrollment-firtst-step-dialog/token-enrollment-first-step-dialog.component';

// Interface for the initialization options of the WebAuthn token (first step)
export interface WebauthnEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'webauthn';
  // No additional type-specific fields for the *first* enrollment call (init)
  // The more complex data is sent in the second step after browser interaction.
}

// Interface for the parameters of the *second* enrollment call (after browser interaction)
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
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-webauthn.component.html',
  styleUrl: './enroll-webauthn.component.scss',
})
export class EnrollWebauthnComponent implements OnInit {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'webauthn')?.text;

  @Output() aditionalFormFieldsChange = new EventEmitter<{
    [key: string]: FormControl<any>;
  }>();
  @Output() clickEnrollChange = new EventEmitter<
    (
      basicOptions: BasicEnrollmentOptions,
    ) => Observable<EnrollmentResponse> | undefined
  >();

  // WebAuthn has no form fields in this component to be filled directly by the user
  webauthnForm = new FormGroup({});

  constructor(
    private notificationService: NotificationService,
    private tokenService: TokenService,
    private base64Service: Base64Service,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.aditionalFormFieldsChange.emit({});
    this.clickEnrollChange.emit(this.onClickEnroll);
  }

  onClickEnroll = (
    basicOptions: BasicEnrollmentOptions,
  ): Observable<EnrollmentResponse> | undefined => {
    if (!navigator.credentials?.create) {
      const errorMsg = 'WebAuthn is not supported by this browser.';
      this.notificationService.openSnackBar(errorMsg);
      return throwError(() => new Error(errorMsg));
    }

    let firstStepDialogRef:
      | MatDialogRef<TokenEnrollmentFirstStepDialogComponent>
      | undefined;

    // Step 1: Initial enrollment call to get challenge etc.
    return this.tokenService
      .enrollToken<WebauthnEnrollmentOptions>({
        ...basicOptions,
        type: 'webauthn',
      })
      .pipe(
        switchMap((responseStep1) => {
          const detail = responseStep1.detail;
          const requestFromStep1 = detail?.webAuthnRegisterRequest;

          if (!requestFromStep1) {
            this.notificationService.openSnackBar(
              'Failed to initiate WebAuthn registration: Invalid server response.',
            );
            return throwError(
              () =>
                new Error('Invalid server response for WebAuthn initiation.'),
            );
          }

          firstStepDialogRef = this.dialog.open(
            TokenEnrollmentFirstStepDialogComponent,
            {
              data: { response: responseStep1 },
              disableClose: true,
            },
          );

          const publicKeyOptions: PublicKeyCredentialCreationOptions = {
            rp: {
              id: requestFromStep1.relyingParty?.id,
              name: requestFromStep1.relyingParty.name,
            },
            user: {
              id: new TextEncoder().encode(requestFromStep1.serialNumber),
              name: requestFromStep1.name,
              displayName: requestFromStep1.displayName,
            },
            challenge: this.base64Service.base64URLToBytes(
              requestFromStep1.nonce,
            ),
            pubKeyCredParams: requestFromStep1.pubKeyCredAlgorithms,
            timeout: requestFromStep1.timeout,
            excludeCredentials: requestFromStep1.excludeCredentials
              ? requestFromStep1.excludeCredentials.map((cred: any) => ({
                  id: this.base64Service.base64URLToBytes(cred.id),
                  type: cred.type,
                  transports: cred.transports,
                }))
              : [],
            authenticatorSelection: requestFromStep1.authenticatorSelection,
            attestation: requestFromStep1.attestation,
            extensions: requestFromStep1.extensions,
          };

          // Step 2: Browser API interaction
          return from(
            navigator.credentials.create({ publicKey: publicKeyOptions }),
          ).pipe(
            // Step 3: Final enrollment call with browser response
            switchMap((publicKeyCred: any) => {
              if (!publicKeyCred) {
                return throwError(
                  () => new Error('WebAuthn credential creation failed.'),
                );
              }
              const params: any = {
                type: 'webauthn',
                transaction_id: requestFromStep1.transaction_id,
                serial: requestFromStep1.serialNumber,
                credential_id: publicKeyCred.id, // This is an ArrayBuffer
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
              if (extResults?.credProps) {
                params.credProps = extResults.credProps;
              }
              return this.tokenService.enrollToken(params).pipe(
                catchError((errorStep3) => {
                  this.notificationService.openSnackBar(
                    'Error during final WebAuthn registration step. Attempting to clean up token.',
                  );
                  return from(
                    this.tokenService.deleteToken(
                      requestFromStep1.serialNumber,
                    ),
                  ).pipe(
                    switchMap(() => {
                      this.notificationService.openSnackBar(
                        `Token ${requestFromStep1.serialNumber} deleted due to registration error.`,
                      );
                      return throwError(() => errorStep3);
                    }),
                    catchError((deleteError) => {
                      this.notificationService.openSnackBar(
                        `Failed to delete token ${requestFromStep1.serialNumber} after registration error. Please check manually.`,
                      );
                      return throwError(() => errorStep3);
                    }),
                  );
                }),
              );
            }),
            catchError((browserOrCredentialError) => {
              this.notificationService.openSnackBar(
                `WebAuthn credential creation failed: ${browserOrCredentialError.message}`,
              );
              return throwError(() => browserOrCredentialError);
            }),
          );
        }),
        catchError((error) => {
          const errMsg = `WebAuthn registration process failed: ${error.message || error}`;
          this.notificationService.openSnackBar(errMsg);
          return throwError(() => error);
        }),
        finalize(() => {
          if (firstStepDialogRef) {
            firstStepDialogRef.close();
          }
        }),
      );
  };
}
